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
    // 允许内网穿透（cpolar 等）的公网域名访问 dev server
    // Vite 5.2+ 默认只放行 localhost 的 Host 头，公网域名会被 403 拦截
    // 仅 dev server 生效，不影响 build 后的产物；用 true 表示放开所有 Host（测试用）
    allowedHosts: true,
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
