<template>
  <div id="app">
    <el-container>
      <el-header>
        <div class="header-content">
          <h1>📸 Photo-Score 摄影点评</h1>
          <p class="subtitle">基于 AI 的专业摄影作品点评系统</p>
        </div>
      </el-header>
      <el-main>
        <Home />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import Home from './views/Home.vue'
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
}

#app {
  min-height: 100vh;
}

.el-header {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  padding: 20px 40px;
}

.header-content {
  text-align: center;
}

.header-content h1 {
  font-size: 28px;
  color: #333;
  margin-bottom: 5px;
}

.subtitle {
  color: #666;
  font-size: 14px;
}

.el-main {
  padding: 40px;
  max-width: 1200px;
  margin: 0 auto;
}
</style>
