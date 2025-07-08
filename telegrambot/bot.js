const { Telegraf } = require('telegraf');
require('dotenv').config();

const BOT_TOKEN = process.env.BOT_TOKEN;
const WEB_APP_URL = process.env.WEB_APP_URL;

const bot = new Telegraf(BOT_TOKEN);

bot.start((ctx) => {
  console.log(WEB_APP_URL);
  ctx.reply('Откройте мини-приложение:', {
    reply_markup: {
      keyboard: [
        [
          {
            text: 'Открыть список машин',
            web_app: { url: WEB_APP_URL }
          }
        ]
      ],
      resize_keyboard: true,
      one_time_keyboard: true
    }
  });
});

bot.launch();

process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
