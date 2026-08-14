import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'

// تبدیل آدرس فایل فعلی به مسیر دایرکتوری
const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export default defineConfig({
  plugins: [react()],
  // ریشه را دقیقاً به دایرکتوری که این فایل در آن قرار دارد تنظیم می‌کند
  root: __dirname,
  server: {
    host: '0.0.0.0',      // گوش دادن روی تمام شبکه (برای تست با IP)
    port: 5173,
    strictPort: true,      // اگر پورت اشغال بود خطا بدهد (برای عیب‌یابی)
  },
  // (اختیاری) اگر پوشه public دارید، مطمئن شوید مسیر آن درست است
  publicDir: path.join(__dirname, 'public'),
  // برای رفع مشکل کش در برخی مرورگرها
  optimizeDeps: {
    force: true,
  },
})