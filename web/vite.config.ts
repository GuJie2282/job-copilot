import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true
      }
    }
  },
  css: {
    preprocessorOptions: {
      scss: {
        // 把 variables.scss 注入到每个 scss 文件前，使任意组件可直接用 $token
        // 但排除 variables.scss 自身，否则会「自己 @use 自己」造成模块循环
        additionalData(source: string, filename: string) {
          if (filename.replace(/\\/g, '/').endsWith('src/styles/variables.scss')) {
            return source
          }
          return `@use "@/styles/variables.scss" as *;\n${source}`
        }
      }
    }
  }
})
