<template>
  <div class="critique-tab">
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
              <div class="upload-hint">支持 JPG、PNG、WebP 格式</div>
            </div>
          </el-upload>
          
          <el-button
            type="primary"
            size="large"
            class="critique-btn"
            :loading="loading"
            :disabled="!selectedFile"
            @click="handleCritique"
          >
            {{ loading ? '分析中...' : '开始点评' }}
          </el-button>
        </div>
      </el-col>
      
      <el-col :span="14">
        <div class="result-section">
          <CritiqueResult v-if="result" :result="result" />
          <div v-else class="empty-result">
            <el-empty description="上传图片后点击「开始点评」" />
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { critiqueImage } from '../api'
import CritiqueResult from './CritiqueResult.vue'

const selectedFile = ref(null)
const imageUrl = ref('')
const loading = ref(false)
const result = ref(null)

const handleFileChange = (file) => {
  selectedFile.value = file.raw
  imageUrl.value = URL.createObjectURL(file.raw)
  result.value = null
}

const handleCritique = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先上传图片')
    return
  }
  
  loading.value = true
  
  try {
    const response = await critiqueImage(selectedFile.value)
    
    if (response.success) {
      result.value = response.data
      ElMessage.success('点评完成')
    } else {
      ElMessage.error('点评失败')
    }
  } catch (error) {
    console.error('Critique error:', error)
    ElMessage.error('点评失败，请检查后端服务是否启动')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.critique-tab {
  min-height: 450px;
}

.upload-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.image-uploader {
  width: 100%;
}

.image-uploader :deep(.el-upload) {
  width: 100%;
}

.image-uploader :deep(.el-upload-dragger) {
  width: 100%;
  height: 300px;
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
  max-height: 280px;
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

.upload-hint {
  margin-top: 5px;
  font-size: 12px;
  color: #909399;
}

.critique-btn {
  width: 200px;
  height: 45px;
  font-size: 16px;
  border-radius: 8px;
}

.result-section {
  min-height: 400px;
}

.empty-result {
  height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
