import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000
})

/**
 * 点评图片
 * @param {File} file 图片文件
 * @returns {Promise} 点评结果
 */
export async function critiqueImage(file) {
  const formData = new FormData()
  formData.append('file', file)
  
  const response = await api.post('/critique', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  
  return response.data
}

/**
 * 多轮对话
 * @param {File} file 图片文件
 * @param {string} question 用户问题
 * @param {string} sessionId 会话 ID
 * @returns {Promise} 对话结果
 */
export async function chatWithImage(file, question, sessionId = 'default') {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('question', question)
  formData.append('session_id', sessionId)
  
  const response = await api.post('/chat', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  
  return response.data
}

/**
 * 清除对话历史
 * @param {string} sessionId 会话 ID
 * @returns {Promise} 操作结果
 */
export async function clearChatHistory(sessionId = 'default') {
  const formData = new FormData()
  formData.append('session_id', sessionId)
  
  const response = await api.post('/chat/clear', formData)
  return response.data
}

export default api
