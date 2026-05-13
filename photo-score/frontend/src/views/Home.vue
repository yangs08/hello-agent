<template>
  <div class="home">
    <el-tabs v-model="activeTab" type="border-card" class="main-tabs">
      <el-tab-pane label="📷 单张点评" name="critique">
        <CritiqueTab />
      </el-tab-pane>
      <el-tab-pane label="💬 多轮对话" name="chat">
        <ChatTab />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import CritiqueTab from '../components/CritiqueTab.vue'
import ChatTab from '../components/ChatTab.vue'

const activeTab = ref('critique')
</script>

<style scoped>
.home {
  width: 100%;
}

.main-tabs {
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

:deep(.el-tabs__header) {
  background: #f5f7fa;
}

:deep(.el-tabs__item) {
  font-size: 16px;
  padding: 0 30px;
  height: 50px;
  line-height: 50px;
}

:deep(.el-tabs__content) {
  padding: 30px;
  min-height: 500px;
}
</style>
