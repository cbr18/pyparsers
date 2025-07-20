require('dotenv').config({ path: require('path').resolve(__dirname, '../.env') });
const { Telegraf } = require('telegraf');
const express = require('express');

const app = express();
app.use(express.json());

const bot = new Telegraf(process.env.TELEGRAM_BOT_TOKEN);

// /start command
bot.start((ctx) => ctx.reply('Бот для заявок CarCatch активен!'));

// Endpoint to receive lead requests from frontend
app.post('/lead', async (req, res) => {
  const { car, user } = req.body;
  if (!car) {
    return res.status(400).json({ error: 'No car data provided' });
  }
  // Compose message
  let msg = `🚗 Новая заявка с сайта\n`;
  if (user) msg += `Пользователь: ${user}\n`;
  msg += `Бренд: ${car.brand_name || '-'}\n`;
  msg += `Модель: ${car.car_name || '-'}\n`;
  msg += `Год: ${car.year || '-'}\n`;
  msg += `Город: ${car.city || '-'}\n`;
  msg += `Цена: ${car.price || '-'}\n`;
  msg += `Ссылка: ${car.link || '-'}\n`;

  try {
    // Send to @Maksim_CarCatch (username)
    await bot.telegram.sendMessage(process.env.LEAD_TARGET_CHAT || '@Maksim_CarCatch', msg, { parse_mode: 'Markdown' });
    res.json({ ok: true });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Express server listening on port ${PORT}`);
  bot.launch();
  console.log('Telegram bot started');
});

// Graceful stop
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM')); 