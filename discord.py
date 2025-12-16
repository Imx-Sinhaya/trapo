const { Client, GatewayIntentBits, EmbedBuilder, PermissionFlagsBits, ChannelType, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');
require('dotenv').config();

const client = new Client({ 
  intents: [
    GatewayIntentBits.Guilds, 
    GatewayIntentBits.GuildMessages, 
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.GuildMembers,
    GatewayIntentBits.GuildModeration
  ] 
});

// Increase max listeners to prevent warning (we have many command handlers)
client.setMaxListeners(20);

// ============ CONFIGURATION ============
const CONFIG = {
  COMMAND_PREFIX: process.env.COMMAND_PREFIX || '!', // Command prefix (e.g., '!', 'tc!', '?')
  AUTO_NICKNAME_PREFIX: 'TC|', // Prefix for auto-nickname
  WELCOME_ROLE_NAME: 'Member', // Auto role for new members
  LOG_CHANNEL_NAME: 'mod-logs', // Moderation log channel
  TICKET_CATEGORY_NAME: 'Support Tickets', // Category for tickets
  DEFAULT_NICKNAME_FORMAT: (username) => `${CONFIG.AUTO_NICKNAME_PREFIX} ${username}`,
};

// ============ DATA STORAGE ============
const warnings = new Map(); // userId -> [{ moderator, reason, timestamp }]
const activeTickets = new Map(); // channelId -> { userId, reason, timestamp }

// ============ HELPER FUNCTIONS ============
async function getLogChannel(guild) {
  let channel = guild.channels.cache.find(ch => ch.name === CONFIG.LOG_CHANNEL_NAME);
  if (!channel) {
    try {
      channel = await guild.channels.create({
        name: CONFIG.LOG_CHANNEL_NAME,
        type: ChannelType.GuildText,
        permissionOverwrites: [
          {
            id: guild.roles.everyone.id,
            deny: [PermissionFlagsBits.ViewChannel],
          },
        ],
      });
      console.log(`Created log channel: ${CONFIG.LOG_CHANNEL_NAME}`);
    } catch (error) {
      console.error('Failed to create log channel:', error);
    }
  }
  return channel;
}

async function createSupportTicket(guild, userId, reason, moderatorId) {
  try {
    // Find or create ticket category
    let category = guild.channels.cache.find(ch => ch.name === CONFIG.TICKET_CATEGORY_NAME && ch.type === ChannelType.GuildCategory);
    if (!category) {
      category = await guild.channels.create({
        name: CONFIG.TICKET_CATEGORY_NAME,
        type: ChannelType.GuildCategory,
      });
    }

    // Create ticket channel
    const ticketNumber = Date.now();
    const user = await guild.members.fetch(userId);
    const ticketChannel = await guild.channels.create({
      name: `ticket-${user.user.username}-${ticketNumber}`,
      type: ChannelType.GuildText,
      parent: category.id,
      permissionOverwrites: [
        {
          id: guild.roles.everyone.id,
          deny: [PermissionFlagsBits.ViewChannel],
        },
        {
          id: userId,
          allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages, PermissionFlagsBits.ReadMessageHistory],
        },
      ],
    });

    activeTickets.set(ticketChannel.id, { userId, reason, timestamp: Date.now() });

    const moderator = await guild.members.fetch(moderatorId);
    const ticketEmbed = new EmbedBuilder()
      .setTitle('🎫 Support Ticket Created')
      .setColor(0xe74c3c)
      .setDescription(`**Reason for Ticket Creation:**\n${reason}`)
      .addFields(
        { name: '👤 User', value: `${user.user.tag} (${userId})`, inline: true },
        { name: '👮 Moderator', value: `${moderator.user.tag}`, inline: true },
        { name: '⏰ Created', value: `<t:${Math.floor(Date.now() / 1000)}:F>`, inline: false }
      )
      .setFooter({ text: 'Please explain your situation. A staff member will assist you shortly.' });

    const closeButton = new ActionRowBuilder()
      .addComponents(
        new ButtonBuilder()
          .setCustomId('close_ticket')
          .setLabel('Close Ticket')
          .setStyle(ButtonStyle.Danger)
          .setEmoji('🔒')
      );

    await ticketChannel.send({ content: `<@${userId}> <@${moderatorId}>`, embeds: [ticketEmbed], components: [closeButton] });
    return ticketChannel;
  } catch (error) {
    console.error('Failed to create support ticket:', error);
    return null;
  }
}

async function logModeration(guild, action, target, moderator, reason, extraFields = []) {
  const logChannel = await getLogChannel(guild);
  if (!logChannel) return;

  const embed = new EmbedBuilder()
    .setTitle(`🛡️ Moderation Action: ${action}`)
    .setColor(0xe67e22)
    .addFields(
      { name: '👤 Target', value: `${target.tag || target.user?.tag} (${target.id})`, inline: true },
      { name: '👮 Moderator', value: `${moderator.tag} (${moderator.id})`, inline: true },
      { name: '📝 Reason', value: reason || 'No reason provided', inline: false },
      ...extraFields
    )
    .setTimestamp()
    .setFooter({ text: `Action: ${action}` });

  await logChannel.send({ embeds: [embed] });
}


// ============ HELPER: COMMAND FUNCTIONS ============
function isCommand(message, command) {
  return message.content === `${CONFIG.COMMAND_PREFIX}${command}` || 
         message.content.startsWith(`${CONFIG.COMMAND_PREFIX}${command} `);
}

function getCommand(message) {
  if (!message.content.startsWith(CONFIG.COMMAND_PREFIX)) return null;
  return message.content.slice(CONFIG.COMMAND_PREFIX.length).trim();
}

// ============ EVENT: BOT READY ============
client.once('clientReady', () => {
  console.log(`✅ Trapo Cloud Bot is online! Logged in as ${client.user.tag}`);
  console.log(`📝 Command Prefix: ${CONFIG.COMMAND_PREFIX}`);
  client.user.setActivity(`Trapo Cloud | ${CONFIG.COMMAND_PREFIX}help`, { type: 'WATCHING' });
});

// ============ EVENT: NEW MEMBER ============
client.on('guildMemberAdd', async member => {
  try {
    // 1. Set auto nickname
    const newNickname = CONFIG.DEFAULT_NICKNAME_FORMAT(member.user.username);
    await member.setNickname(newNickname).catch(err => console.log('Cannot set nickname:', err.message));

    // 2. Assign welcome role
    const welcomeRole = member.guild.roles.cache.find(role => role.name === CONFIG.WELCOME_ROLE_NAME);
    if (welcomeRole) {
      await member.roles.add(welcomeRole).catch(err => console.log('Cannot assign role:', err.message));
    }

    // 3. Send welcome message
    const welcomeChannel = member.guild.channels.cache.find(ch => ch.name === 'welcome' || ch.name === 'general');
    if (welcomeChannel) {
      const welcomeEmbed = new EmbedBuilder()
        .setTitle('👋 Welcome to Trapo Cloud!')
        .setDescription(`Welcome ${member}! We're glad to have you here at **Trapo Cloud**!`)
        .setColor(0x2ecc71)
        .addFields(
          { name: '📋 Read the Rules', value: 'Make sure to check out our server rules!', inline: false },
          { name: '🎫 Need Help?', value: 'Use `!ticket` to create a support ticket!', inline: false },
          { name: '📜 Commands', value: 'Type `!help` to see all available commands!', inline: false }
        )
        .setThumbnail(member.user.displayAvatarURL({ dynamic: true }))
        .setTimestamp();

      await welcomeChannel.send({ embeds: [welcomeEmbed] });
    }

    // 4. Log the join
    const logChannel = await getLogChannel(member.guild);
    if (logChannel) {
      const joinEmbed = new EmbedBuilder()
        .setTitle('📥 New Member Joined')
        .setColor(0x2ecc71)
        .addFields(
          { name: '👤 User', value: `${member.user.tag} (${member.id})`, inline: true },
          { name: '🏷️ Nickname Set', value: newNickname, inline: true },
          { name: '📅 Account Created', value: `<t:${Math.floor(member.user.createdTimestamp / 1000)}:R>`, inline: false }
        )
        .setThumbnail(member.user.displayAvatarURL({ dynamic: true }))
        .setTimestamp();

      await logChannel.send({ embeds: [joinEmbed] });
    }
  } catch (error) {
    console.error('Error in guildMemberAdd event:', error);
  }
});

// ============ EVENT: MEMBER LEAVE ============
client.on('guildMemberRemove', async member => {
  const logChannel = await getLogChannel(member.guild);
  if (logChannel) {
    const leaveEmbed = new EmbedBuilder()
      .setTitle('📤 Member Left')
      .setColor(0xe74c3c)
      .addFields(
        { name: '👤 User', value: `${member.user.tag} (${member.id})`, inline: true },
        { name: '📅 Joined Server', value: `<t:${Math.floor(member.joinedTimestamp / 1000)}:R>`, inline: true }
      )
      .setThumbnail(member.user.displayAvatarURL({ dynamic: true }))
      .setTimestamp();

    await logChannel.send({ embeds: [leaveEmbed] });
  }
});

// ============ VPS HOSTING COMMAND ============
client.on('messageCreate', message => {
  if (isCommand(message, 'vps')) {
    const vpsPrices = {
      "64GB RAM": 8000,
      "32GB RAM": 400,
      "16GB RAM": 2000,
      "8GB RAM": 1000,
      "4GB RAM": 500
    };

    const embed = new EmbedBuilder()
      .setTitle('🖥️ VPS Hosting Plans (LKR)')
      .setColor(0x3498db)
      .setDescription('🎟️ Create a ticket to purchase!')
      .addFields(
        { name: '💠 64GB RAM', value: `Rs. ${vpsPrices["64GB RAM"]}`, inline: false },
        { name: '💠 32GB RAM', value: `Rs. ${vpsPrices["32GB RAM"]}`, inline: false },
        { name: '💠 16GB RAM', value: `Rs. ${vpsPrices["16GB RAM"]}`, inline: false },
        { name: '💠 8GB RAM', value: `Rs. ${vpsPrices["8GB RAM"]}`, inline: false },
        { name: '💠 4GB RAM', value: `Rs. ${vpsPrices["4GB RAM"]}`, inline: false }
      )
      .setFooter({ text: 'Trapo Cloud Hosting™ | Visit trapo.cloud' });
    message.channel.send({ embeds: [embed] });
  }
});

// ============ GAME SERVER HOSTING COMMAND ============
client.on('messageCreate', message => {
  if (isCommand(message, 'gameserver')) {
    const vpsPrices = {
      "64GB RAM": 8000,
      "32GB RAM": 400,
      "16GB RAM": 2000,
      "8GB RAM": 1000,
      "4GB RAM": 500
    };

    const embed = new EmbedBuilder()
      .setTitle('🎮 Game Server Hosting (LKR)')
      .setColor(0xe67e22)
      .setDescription('🎟️ Create a ticket to purchase!')
      .addFields(
        { name: '💠 64GB RAM', value: `Rs. ${vpsPrices["64GB RAM"] + 100}`, inline: false },
        { name: '💠 32GB RAM', value: `Rs. ${vpsPrices["32GB RAM"] + 100}`, inline: false },
        { name: '💠 16GB RAM', value: `Rs. ${vpsPrices["16GB RAM"] + 100}`, inline: false },
        { name: '💠 8GB RAM', value: `Rs. ${vpsPrices["8GB RAM"] + 100}`, inline: false },
        { name: '💠 4GB RAM', value: `Rs. ${vpsPrices["4GB RAM"] + 100}`, inline: false }
      )
      .setFooter({ text: 'Trapo Cloud Hosting™ | Visit trapo.cloud' });
    message.channel.send({ embeds: [embed] });
  }
});

// ============ DISCORD BOT HOSTING COMMAND ============
client.on('messageCreate', message => {
  if (isCommand(message, 'dcbot')) {
    const embed = new EmbedBuilder()
      .setTitle('🤖 Discord Bot Hosting Plans (LKR)')
      .setColor(0x9b59b6)
      .setDescription('🎟️ Create a ticket to purchase!')
      .addFields(
        { name: '🟢 Starter', value: '💲 Rs. 100\n🧠 RAM: 256MB', inline: false },
        { name: '🔵 Coder', value: '💲 Rs. 200\n🧠 RAM: 512MB', inline: false },
        { name: '🟣 Developer', value: '💲 Rs. 600\n🧠 RAM: 1GB', inline: false }
      )
      .setFooter({ text: 'CodeOn Hosting™ | Visit codeon.codes' });
    message.channel.send({ embeds: [embed] });
  }
});

// ============ WEB HOSTING COMMAND ============
client.on('messageCreate', message => {
  if (isCommand(message, 'web')) {
    const embed = new EmbedBuilder()
      .setTitle('🌐 Web Hosting Plans (LKR)')
      .setColor(0x2ecc71)
      .setDescription('🎟️ Create a ticket to purchase!')
      .addFields(
        { name: 'Lite', value: '💲 Rs. 99\n💾 SSD: 1GB', inline: false },
        { name: 'Plus', value: '💲 Rs. 199\n💾 SSD: 5GB', inline: false },
        { name: 'Elite', value: '💲 Rs. 399\n💾 SSD: 10GB', inline: false }
      )
      .setFooter({ text: 'Trapo Cloud Hosting™ | Visit trapo.cloud' });
    message.channel.send({ embeds: [embed] });
  }
});

// ============ HELP COMMAND ============
client.on('messageCreate', message => {
  if (isCommand(message, 'help')) {
    const embed = new EmbedBuilder()
      .setTitle('📚 Trapo Cloud - Bot Commands')
      .setColor(0x3498db)
      .setDescription('Here are all available commands for **Trapo Cloud**:')
      .addFields(
        { name: '💼 Hosting Commands', value: '`!vps` - VPS hosting plans\n`!gameserver` - Game server plans\n`!dcbot` - Discord bot hosting\n`!web` - Web hosting plans', inline: false },
        { name: '🎫 Support', value: '`!ticket [reason]` - Create a support ticket', inline: false },
        { name: '🛡️ Moderation (Admin Only)', value: '`!warn @user [reason]` - Warn a user\n`!kick @user [reason]` - Kick a user\n`!ban @user [reason]` - Ban a user\n`!timeout @user [minutes] [reason]` - Timeout a user\n`!warnings @user` - Check user warnings\n`!clearwarnings @user` - Clear warnings\n`!nicknameall` - Set TC| for all members\n`!nicknameall force` - Force TC| for everyone', inline: false },
        { name: '⚙️ Utility', value: '`!serverinfo` - Server information\n`!userinfo [@user]` - User information\n`!ping` - Check bot latency', inline: false }
      )
      .setFooter({ text: 'Trapo Cloud™ - Premium Hosting Services' })
      .setTimestamp();
    message.channel.send({ embeds: [embed] });
  }
});

// ============ TICKET COMMAND ============
client.on('messageCreate', async message => {
  if (isCommand(message, 'ticket')) {
    if (message.author.bot) return;
    
    const reason = message.content.slice(8).trim() || 'General Support Request';
    const ticket = await createSupportTicket(message.guild, message.author.id, reason, client.user.id);
    
    if (ticket) {
      message.reply(`✅ Support ticket created: ${ticket}`);
    } else {
      message.reply('❌ Failed to create ticket. Please contact an administrator.');
    }
  }
});

// ============ WARN COMMAND ============
client.on('messageCreate', async message => {
  if (isCommand(message, 'warn')) {
    if (message.author.bot) return;
    if (!message.member.permissions.has(PermissionFlagsBits.ModerateMembers)) {
      return message.reply('❌ You do not have permission to use this command.');
    }

    const args = message.content.slice(6).trim().split(/ +/);
    const user = message.mentions.users.first();
    const reason = args.slice(1).join(' ') || 'No reason provided';

    if (!user) {
      return message.reply('❌ Please mention a user to warn.');
    }

    // Add warning to storage
    if (!warnings.has(user.id)) {
      warnings.set(user.id, []);
    }
    warnings.get(user.id).push({
      moderator: message.author.tag,
      reason,
      timestamp: Date.now()
    });

    const warnCount = warnings.get(user.id).length;

    // Send response
    const warnEmbed = new EmbedBuilder()
      .setTitle('⚠️ User Warned')
      .setColor(0xf39c12)
      .addFields(
        { name: '👤 User', value: `${user.tag}`, inline: true },
        { name: '👮 Moderator', value: `${message.author.tag}`, inline: true },
        { name: '📝 Reason', value: reason, inline: false },
        { name: '📊 Total Warnings', value: `${warnCount}`, inline: true }
      )
      .setTimestamp();

    message.channel.send({ embeds: [warnEmbed] });

    // Log moderation
    await logModeration(message.guild, 'WARN', user, message.author, reason, [
      { name: '📊 Total Warnings', value: `${warnCount}`, inline: true }
    ]);

    // Create support ticket
    await createSupportTicket(message.guild, user.id, `User was warned: ${reason}`, message.author.id);

    // DM the user
    try {
      await user.send(`⚠️ You have been warned in **${message.guild.name}**\n**Reason:** ${reason}\n**Total Warnings:** ${warnCount}\n\nA support ticket has been created for you to discuss this action.`);
    } catch (error) {
      console.log('Cannot DM user:', error.message);
    }
  }
});

// ============ KICK COMMAND ============
client.on('messageCreate', async message => {
  if (isCommand(message, 'kick')) {
    if (message.author.bot) return;
    if (!message.member.permissions.has(PermissionFlagsBits.KickMembers)) {
      return message.reply('❌ You do not have permission to use this command.');
    }

    const args = message.content.slice(6).trim().split(/ +/);
    const member = message.mentions.members.first();
    const reason = args.slice(1).join(' ') || 'No reason provided';

    if (!member) {
      return message.reply('❌ Please mention a user to kick.');
    }

    if (!member.kickable) {
      return message.reply('❌ I cannot kick this user.');
    }

    // Create ticket before kicking
    await createSupportTicket(message.guild, member.id, `User was kicked: ${reason}`, message.author.id);

    // DM user before kicking
    try {
      await member.send(`👢 You have been kicked from **${message.guild.name}**\n**Reason:** ${reason}\n\nA support ticket has been created. You may rejoin and appeal this action.`);
    } catch (error) {
      console.log('Cannot DM user:', error.message);
    }

    // Kick the member
    await member.kick(reason);

    // Send confirmation
    const kickEmbed = new EmbedBuilder()
      .setTitle('👢 User Kicked')
      .setColor(0xe67e22)
      .addFields(
        { name: '👤 User', value: `${member.user.tag}`, inline: true },
        { name: '👮 Moderator', value: `${message.author.tag}`, inline: true },
        { name: '📝 Reason', value: reason, inline: false }
      )
      .setTimestamp();

    message.channel.send({ embeds: [kickEmbed] });

    // Log moderation
    await logModeration(message.guild, 'KICK', member.user, message.author, reason);
  }
});

// ============ BAN COMMAND ============
client.on('messageCreate', async message => {
  if (isCommand(message, 'ban')) {
    if (message.author.bot) return;
    if (!message.member.permissions.has(PermissionFlagsBits.BanMembers)) {
      return message.reply('❌ You do not have permission to use this command.');
    }

    const args = message.content.slice(5).trim().split(/ +/);
    const member = message.mentions.members.first();
    const reason = args.slice(1).join(' ') || 'No reason provided';

    if (!member) {
      return message.reply('❌ Please mention a user to ban.');
    }

    if (!member.bannable) {
      return message.reply('❌ I cannot ban this user.');
    }

    // Create ticket before banning
    await createSupportTicket(message.guild, member.id, `User was banned: ${reason}`, message.author.id);

    // DM user before banning
    try {
      await member.send(`🔨 You have been banned from **${message.guild.name}**\n**Reason:** ${reason}\n\nA support ticket has been created for appeals.`);
    } catch (error) {
      console.log('Cannot DM user:', error.message);
    }

    // Ban the member
    await member.ban({ reason });

    // Send confirmation
    const banEmbed = new EmbedBuilder()
      .setTitle('🔨 User Banned')
      .setColor(0xe74c3c)
      .addFields(
        { name: '👤 User', value: `${member.user.tag}`, inline: true },
        { name: '👮 Moderator', value: `${message.author.tag}`, inline: true },
        { name: '📝 Reason', value: reason, inline: false }
      )
      .setTimestamp();

    message.channel.send({ embeds: [banEmbed] });

    // Log moderation
    await logModeration(message.guild, 'BAN', member.user, message.author, reason);
  }
});

// ============ TIMEOUT COMMAND ============
client.on('messageCreate', async message => {
  if (isCommand(message, 'timeout')) {
    if (message.author.bot) return;
    if (!message.member.permissions.has(PermissionFlagsBits.ModerateMembers)) {
      return message.reply('❌ You do not have permission to use this command.');
    }

    const args = message.content.slice(9).trim().split(/ +/);
    const member = message.mentions.members.first();
    const duration = parseInt(args[1]) || 10;
    const reason = args.slice(2).join(' ') || 'No reason provided';

    if (!member) {
      return message.reply('❌ Please mention a user to timeout.');
    }

    if (!member.moderatable) {
      return message.reply('❌ I cannot timeout this user.');
    }

    // Timeout the member
    await member.timeout(duration * 60 * 1000, reason);

    // Create ticket
    await createSupportTicket(message.guild, member.id, `User was timed out for ${duration} minutes: ${reason}`, message.author.id);

    // Send confirmation
    const timeoutEmbed = new EmbedBuilder()
      .setTitle('⏱️ User Timed Out')
      .setColor(0xf39c12)
      .addFields(
        { name: '👤 User', value: `${member.user.tag}`, inline: true },
        { name: '👮 Moderator', value: `${message.author.tag}`, inline: true },
        { name: '⏰ Duration', value: `${duration} minutes`, inline: true },
        { name: '📝 Reason', value: reason, inline: false }
      )
      .setTimestamp();

    message.channel.send({ embeds: [timeoutEmbed] });

    // Log moderation
    await logModeration(message.guild, 'TIMEOUT', member.user, message.author, reason, [
      { name: '⏰ Duration', value: `${duration} minutes`, inline: true }
    ]);

    // DM user
    try {
      await member.send(`⏱️ You have been timed out in **${message.guild.name}** for ${duration} minutes\n**Reason:** ${reason}\n\nA support ticket has been created for you.`);
    } catch (error) {
      console.log('Cannot DM user:', error.message);
    }
  }
});

// ============ CHECK WARNINGS COMMAND ============
client.on('messageCreate', message => {
  if (isCommand(message, 'warnings')) {
    const user = message.mentions.users.first() || message.author;
    const userWarnings = warnings.get(user.id) || [];

    if (userWarnings.length === 0) {
      return message.reply(`✅ ${user.tag} has no warnings.`);
    }

    const embed = new EmbedBuilder()
      .setTitle(`⚠️ Warnings for ${user.tag}`)
      .setColor(0xf39c12)
      .setDescription(`Total Warnings: **${userWarnings.length}**`)
      .setThumbnail(user.displayAvatarURL({ dynamic: true }));

    userWarnings.forEach((warn, index) => {
      embed.addFields({
        name: `Warning #${index + 1}`,
        value: `**Moderator:** ${warn.moderator}\n**Reason:** ${warn.reason}\n**Date:** <t:${Math.floor(warn.timestamp / 1000)}:F>`,
        inline: false
      });
    });

    message.channel.send({ embeds: [embed] });
  }
});

// ============ CLEAR WARNINGS COMMAND ============
client.on('messageCreate', async message => {
  if (isCommand(message, 'clearwarnings')) {
    if (!message.member.permissions.has(PermissionFlagsBits.Administrator)) {
      return message.reply('❌ You need Administrator permission to clear warnings.');
    }

    const user = message.mentions.users.first();
    if (!user) {
      return message.reply('❌ Please mention a user to clear warnings.');
    }

    warnings.delete(user.id);
    message.reply(`✅ Cleared all warnings for ${user.tag}`);

    await logModeration(message.guild, 'CLEAR WARNINGS', user, message.author, 'All warnings cleared');
  }
});

// ============ SERVER INFO COMMAND ============
client.on('messageCreate', message => {
  if (isCommand(message, 'serverinfo')) {
    const embed = new EmbedBuilder()
      .setTitle(`📊 ${message.guild.name} Server Info`)
      .setColor(0x3498db)
      .setThumbnail(message.guild.iconURL({ dynamic: true }))
      .addFields(
        { name: '👑 Owner', value: `<@${message.guild.ownerId}>`, inline: true },
        { name: '📅 Created', value: `<t:${Math.floor(message.guild.createdTimestamp / 1000)}:R>`, inline: true },
        { name: '👥 Members', value: `${message.guild.memberCount}`, inline: true },
        { name: '📝 Channels', value: `${message.guild.channels.cache.size}`, inline: true },
        { name: '🎭 Roles', value: `${message.guild.roles.cache.size}`, inline: true },
        { name: '😀 Emojis', value: `${message.guild.emojis.cache.size}`, inline: true }
      )
      .setTimestamp();

    message.channel.send({ embeds: [embed] });
  }
});

// ============ USER INFO COMMAND ============
client.on('messageCreate', message => {
  if (isCommand(message, 'userinfo')) {
    const user = message.mentions.users.first() || message.author;
    const member = message.guild.members.cache.get(user.id);

    const embed = new EmbedBuilder()
      .setTitle(`👤 User Info: ${user.tag}`)
      .setColor(0x9b59b6)
      .setThumbnail(user.displayAvatarURL({ dynamic: true }))
      .addFields(
        { name: '🆔 ID', value: user.id, inline: true },
        { name: '📅 Account Created', value: `<t:${Math.floor(user.createdTimestamp / 1000)}:R>`, inline: true },
        { name: '📥 Joined Server', value: member ? `<t:${Math.floor(member.joinedTimestamp / 1000)}:R>` : 'N/A', inline: true },
        { name: '🎭 Roles', value: member ? member.roles.cache.map(r => r.name).slice(0, 5).join(', ') : 'N/A', inline: false }
      )
      .setTimestamp();

    message.channel.send({ embeds: [embed] });
  }
});

// ============ PING COMMAND ============
client.on('messageCreate', message => {
  if (isCommand(message, 'ping')) {
    const latency = Date.now() - message.createdTimestamp;
    const apiLatency = Math.round(client.ws.ping);

    const embed = new EmbedBuilder()
      .setTitle('🏓 Pong!')
      .setColor(0x2ecc71)
      .addFields(
        { name: '⏱️ Latency', value: `${latency}ms`, inline: true },
        { name: '📡 API Latency', value: `${apiLatency}ms`, inline: true }
      )
      .setTimestamp();

    message.channel.send({ embeds: [embed] });
  }
});

// ============ BULK NICKNAME COMMAND ============
client.on('messageCreate', async message => {
  if (isCommand(message, 'nicknameall')) {
    if (message.author.bot) return;
    
    // Check for Administrator permission
    if (!message.member.permissions.has(PermissionFlagsBits.Administrator)) {
      return message.reply('❌ You need Administrator permission to use this command.');
    }

    const args = message.content.split(' ');
    const forceMode = args.includes('force');

    // Send initial message
    const initialEmbed = new EmbedBuilder()
      .setTitle('🔄 Bulk Nickname Update Started')
      .setColor(0xf39c12)
      .setDescription(forceMode 
        ? '**Mode:** Force (overwrites all nicknames)\n**Status:** Fetching members...'
        : '**Mode:** Normal (only users without nicknames)\n**Status:** Fetching members...')
      .setTimestamp();

    const statusMessage = await message.channel.send({ embeds: [initialEmbed] });

    try {
      // Fetch all members
      await message.guild.members.fetch();
      const members = message.guild.members.cache;
      
      let processed = 0;
      let updated = 0;
      let skipped = 0;
      let failed = 0;
      const total = members.size;

      // Update progress every 50 members
      let lastUpdate = Date.now();

      for (const [memberId, member] of members) {
        processed++;

        // Skip bots
        if (member.user.bot) {
          skipped++;
          continue;
        }

        // Skip server owner (can't change their nickname)
        if (member.id === message.guild.ownerId) {
          skipped++;
          continue;
        }

        // Skip if member already has nickname and not in force mode
        if (!forceMode && member.nickname) {
          skipped++;
          continue;
        }

        // Skip if nickname already has the prefix
        if (member.nickname && member.nickname.startsWith(CONFIG.AUTO_NICKNAME_PREFIX)) {
          skipped++;
          continue;
        }

        try {
          const newNickname = CONFIG.DEFAULT_NICKNAME_FORMAT(member.user.username);
          await member.setNickname(newNickname);
          updated++;

          // Rate limiting: wait 1 second between updates
          await new Promise(resolve => setTimeout(resolve, 1000));

          // Update status message every 5 seconds or every 50 members
          if (Date.now() - lastUpdate > 5000 || processed % 50 === 0) {
            const progressEmbed = new EmbedBuilder()
              .setTitle('🔄 Bulk Nickname Update In Progress')
              .setColor(0xf39c12)
              .setDescription(forceMode 
                ? '**Mode:** Force (overwrites all nicknames)'
                : '**Mode:** Normal (only users without nicknames)')
              .addFields(
                { name: '📊 Progress', value: `${processed}/${total} members processed`, inline: true },
                { name: '✅ Updated', value: `${updated}`, inline: true },
                { name: '⏭️ Skipped', value: `${skipped}`, inline: true },
                { name: '❌ Failed', value: `${failed}`, inline: true },
                { name: '⏱️ Estimated Time', value: `~${Math.ceil((total - processed) / 60)} minutes remaining`, inline: false }
              )
              .setTimestamp();

            await statusMessage.edit({ embeds: [progressEmbed] });
            lastUpdate = Date.now();
          }

        } catch (error) {
          failed++;
          console.log(`Failed to set nickname for ${member.user.tag}:`, error.message);
        }
      }

      // Final summary
      const summaryEmbed = new EmbedBuilder()
        .setTitle('✅ Bulk Nickname Update Complete!')
        .setColor(0x2ecc71)
        .setDescription(forceMode 
          ? '**Mode:** Force (overwrites all nicknames)'
          : '**Mode:** Normal (only users without nicknames)')
        .addFields(
          { name: '📊 Total Members', value: `${total}`, inline: true },
          { name: '✅ Successfully Updated', value: `${updated}`, inline: true },
          { name: '⏭️ Skipped', value: `${skipped}`, inline: true },
          { name: '❌ Failed', value: `${failed}`, inline: true },
          { name: '⏱️ Time Taken', value: `~${Math.ceil(updated / 60)} minutes`, inline: false }
        )
        .setFooter({ text: `Requested by ${message.author.tag}` })
        .setTimestamp();

      await statusMessage.edit({ embeds: [summaryEmbed] });

      // Log the bulk action
      await logModeration(message.guild, 'BULK NICKNAME UPDATE', message.author, message.author, 
        `Updated ${updated} nicknames (${forceMode ? 'Force Mode' : 'Normal Mode'})`, [
          { name: '✅ Updated', value: `${updated}`, inline: true },
          { name: '⏭️ Skipped', value: `${skipped}`, inline: true },
          { name: '❌ Failed', value: `${failed}`, inline: true }
        ]);

    } catch (error) {
      console.error('Error in bulk nickname update:', error);
      
      const errorEmbed = new EmbedBuilder()
        .setTitle('❌ Bulk Nickname Update Failed')
        .setColor(0xe74c3c)
        .setDescription(`An error occurred: ${error.message}`)
        .setTimestamp();

      await statusMessage.edit({ embeds: [errorEmbed] });
    }
  }
});

// ============ BUTTON INTERACTION: CLOSE TICKET ============
client.on('interactionCreate', async interaction => {
  if (!interaction.isButton()) return;

  if (interaction.customId === 'close_ticket') {
    const ticketData = activeTickets.get(interaction.channelId);
    if (!ticketData) {
      return interaction.reply({ content: '❌ This is not a valid ticket channel.', ephemeral: true });
    }

    const closeEmbed = new EmbedBuilder()
      .setTitle('🔒 Ticket Closed')
      .setColor(0x95a5a6)
      .setDescription('This ticket has been closed. The channel will be deleted in 5 seconds.')
      .setTimestamp();

    await interaction.reply({ embeds: [closeEmbed] });

    activeTickets.delete(interaction.channelId);

    setTimeout(async () => {
      await interaction.channel.delete();
    }, 5000);
  }
});

// ============ LOGIN ============
client.login(process.env.DISCORD_TOKEN || 'MTQ0NDkwODI3Njg2ODMyMTM3MQ.GnZK1v.BocmEBkGo0PYXw0sclYm1jccuEzvy0Xmsl2fX0');