import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"
import { copyFileSync, mkdirSync, existsSync } from "fs"

function copyServiceWorker() {
  return {
    name: 'copy-service-worker',
    closeBundle() {
      const destDir = path.resolve(__dirname, 'dist')
      if (!existsSync(destDir)) {
        mkdirSync(destDir, { recursive: true })
      }
      copyFileSync(
        path.resolve(__dirname, 'src/sw.js'),
        path.resolve(destDir, 'sw.js')
      )
    }
  }
}

// https://vite.dev/config/
export default defineConfig({
  base: './',
  plugins: [react(), copyServiceWorker()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
