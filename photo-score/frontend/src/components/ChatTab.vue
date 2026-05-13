<template>
  <div class="chat-tab">
    <el-row :gutter="30">
      <el-col :span="10">
        <div class="upload-section">
          <el-upload
            class="image-uploader"
            drag
            :auto-upload="false"
            :on-change="handleFileChange"
            :show-file-list="false"
            accept="image/*"
          >
            <div v-if="imageUrl" class="image-preview">
              <img :src="imageUrl" alt="预览" />
            </div>
            <div v-else class="upload-placeholder">
              <el-icon class="upload-icon"><Plus /></el-icon>
              <div class="upload-text">拖拽或点击上传图片</div>
            </div>
          </el-upload>
          
          <el-button
            type="danger"
            size="small"
            @click="handleClearHistory"
            :disabled="messages.length === 0"
          >
            清除对话历史
          </el-button>
        </div>
      </el-col>
      
      <el-col :span="14">
        <div class="chat-section">
          <div class="messages-container" ref="messagesContainer">
            <div
              v-for="(msg, index) in messages"
              :key="index"
              :class="['message', msg.role]"
            >
              <div class="message-content">
                <div class="message-role">{{ msg.role === 'user' ? '👤 你' : '🤖 AI' }}</div>
                <div class="message-text">{{ msg.content }}</div>
              </div>
            </div>
            
            <div v-if="messages.length === 0" class="empty-chat">
              <el-empty description="上传图片后开始对话" />
            </div>
          </div>
          
          <div class="input-section">
            <el-input
              v-model="inputMessage"
              type="textarea"
              :rows="3"
              placeholder="输入你的问题，例如：构图有什么问题？"
              :disabled="!selectedFile"
              @keydown.enter.ctrl="handleSend"
            />
            <el-button
              type="primary"
              :loading="loading"
              :disabled="!selectedFile || !inputMessage.trim()"
              @click="handleSend"
            >
              发送 (Ctrl+Enter)
            </el-button>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { chatWithImage, clearChatHistory } from '../api'

const selectedFile = ref(null)
const imageUrl = ref('')
const inputMessage = ref('')
const loading = ref(false)
const messages = ref([])
const messagesContainer = ref(null)

const handleFileChange = (file) => {
  selectedFile.value = file.raw
  imageUrl.value = URL.createObjectURL(file.raw)
  messages.value = []
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const handleSend = async () => {
  if (!selectedFile.value || !inputMessage.value.trim()) {
    return
  }
  
  const question = inputMessage.value.trim()
  messages.value.push({ role: 'user', content: question })
  inputMessage.value = ''
  loading.value = true
  
  await scrollToBottom()
  
  try {
    const response = await chatWithImage(selectedFile.value, question)
    
    if (response.success) {
      messages.value.push({
        role: 'assistant',
        content: response.data.response
      })
    } else {
      ElMessage.error('对话失败')
    }
  } catch (error) {
    console.error('Chat error:', error)
    ElMessage.error('对话失败，请检查后端服务是否启动')
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

const handleClearHistory = async () => {
  try {
    await clearChatHistory()
    messages.value = []
    ElMessage.success('历史已清除')
  } catch (error) {
    console.error('Clear history error:', error)
  }
}
</script>

<style scoped>
.chat-tab {
  min-height: 450px;
}

.upload-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
}

.image-uploader {
  width: 100%;
}

.image-uploader :deep(.el-upload) {
  width: 100%;
}

.image-uploader :deep(.el-upload-dragger) {
  width: 100%;
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
}

.image-preview {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-preview img {
  max-width: 100%;
  max-height: 180px;
  object-fit: contain;
  border-radius: 8px;
}

.upload-placeholder {
  text-align: center;
}

.upload-icon {
  font-size: 48px;
  color: #c0c4cc;
}

.upload-text {
  margin-top: 10px;
  font-size: 16px;
  color: #606266;
}

.chat-section {
  display: flex;
  flex-direction: column;
  height: 500px;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 12px 12px 0 0;
  border: 1px solid #e4e7ed;
  border-bottom: none;
}

.message {
  margin-bottom: 20px;
}

.message.user {
  display: flex;
  justify-content: flex-end;
}

.message.assistant {
  display: flex;
  justify-content: flex-start;
}

.message-content {
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 12px;
}

.message.user .message-content {
  background: #409eff;
  color: white;
}

.message.assistant .message-content {
  background: white;
  color: #303133;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.message-role {
  font-size: 12px;
  margin-bottom: 5px;
  opacity: 0.8;
}

.message-text {
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.empty-chat {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.input-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 15px;
  background: white;
  border-radius: 0 0 12px 12px;
  border: 1px solid #e4e7ed;
  border-top: none;
}

.input-section .el-button {
  align-self: flex-end;
}
</style>
