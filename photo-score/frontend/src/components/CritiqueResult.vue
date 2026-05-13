<template>
  <div class="critique-result">
    <el-card class="score-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>📊 评分结果</span>
          <el-tag type="success" size="large">总分: {{ result.total_score }}/10</el-tag>
        </div>
      </template>
      
      <div class="score-grid">
        <div class="score-item" v-for="(item, key) in dimensions" :key="key">
          <div class="score-label">{{ item.label }}</div>
          <el-progress
            :percentage="result[key]?.score * 10"
            :color="getProgressColor(result[key]?.score)"
            :stroke-width="20"
            :text-inside="true"
          />
          <div class="score-analysis">{{ result[key]?.analysis }}</div>
        </div>
      </div>
    </el-card>
    
    <el-card class="comment-card" shadow="hover">
      <template #header>
        <span>💡 总体评价</span>
      </template>
      <p class="overall-comment">{{ result.overall_comment }}</p>
    </el-card>
    
    <el-card class="tips-card" shadow="hover">
      <template #header>
        <span>🎯 改进建议</span>
      </template>
      <ul class="improvement-tips">
        <li v-for="(tip, index) in result.improvement_tips" :key="index">
          {{ tip }}
        </li>
      </ul>
    </el-card>
  </div>
</template>

<script setup>
const props = defineProps({
  result: {
    type: Object,
    required: true
  }
})

const dimensions = {
  technical: { label: '技术质量' },
  composition: { label: '构图' },
  color: { label: '色彩' },
  artistry: { label: '艺术性' }
}

const getProgressColor = (score) => {
  if (score >= 8) return '#67c23a'
  if (score >= 6) return '#e6a23c'
  return '#f56c6c'
}
</script>

<style scoped>
.critique-result {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.score-grid {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.score-item {
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
}

.score-label {
  font-size: 14px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 10px;
}

.score-analysis {
  margin-top: 10px;
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}

.overall-comment {
  font-size: 15px;
  color: #303133;
  line-height: 1.8;
}

.improvement-tips {
  padding-left: 20px;
  margin: 0;
}

.improvement-tips li {
  font-size: 14px;
  color: #606266;
  line-height: 2;
}
</style>
