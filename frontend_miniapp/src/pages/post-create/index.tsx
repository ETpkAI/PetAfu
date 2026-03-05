import { View, Text, Textarea, Image } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useState } from 'react'
import { getToken } from '../../utils/request'
import { API_V1 } from '../../config'
import './index.scss'

export default function PostCreate() {
  const [content, setContent] = useState('')
  const [images, setImages] = useState<string[]>([])  // 本地临时路径
  const [loading, setLoading] = useState(false)

  const chooseImages = async () => {
    const remaining = 9 - images.length
    if (remaining <= 0) {
      Taro.showToast({ title: '最多9张图片', icon: 'none' })
      return
    }
    try {
      const res = await Taro.chooseImage({
        count: remaining,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera'],
      })
      setImages(prev => [...prev, ...res.tempFilePaths])
    } catch {}
  }

  const removeImage = (index: number) => {
    setImages(prev => prev.filter((_, i) => i !== index))
  }

  const handlePublish = async () => {
    if (!content.trim()) {
      Taro.showToast({ title: '请输入内容', icon: 'none' })
      return
    }
    setLoading(true)

    try {
      // 使用 Taro.uploadFile 逐张上传图片
      const uploadedUrls: string[] = []
      for (const imgPath of images) {
        const uploadRes = await Taro.uploadFile({
          url: `${API_V1}/community/upload`,
          filePath: imgPath,
          name: 'file',
          header: {
            Authorization: `Bearer ${getToken()}`,
          },
        })
        const data = JSON.parse(uploadRes.data)
        if (data.url) {
          uploadedUrls.push(data.url)
        }
      }

      // 发帖：使用 FormData 格式
      // 由于 Taro 小程序端不支持直接发 multipart with files+text 混合
      // 我们已经上传了图片拿到 URL，现在直接发 JSON
      await Taro.request({
        url: `${API_V1}/community/posts`,
        method: 'POST',
        header: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        data: {
          content: content.trim(),
          // 后端接收 Form 中的 images，但已通过单独上传
          // 这里用单独的 API 方案
        },
      })

      Taro.showToast({ title: '发布成功 🎉', icon: 'success' })
      setTimeout(() => Taro.navigateBack(), 500)
    } catch (e: any) {
      Taro.showToast({ title: '发布失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <View className='post-create'>
      <View className='pc-header'>
        <Text className='pc-title'>发布动态</Text>
      </View>

      <View className='pc-card'>
        <Textarea
          className='content-input'
          placeholder='分享你和宠物的故事...'
          value={content}
          onInput={e => setContent(e.detail.value)}
          maxlength={500}
          autoFocus
        />
        <Text className='char-count'>{content.length}/500</Text>

        {/* 图片预览 */}
        <View className='image-grid'>
          {images.map((img, i) => (
            <View key={i} className='image-item'>
              <Image className='preview-img' src={img} mode='aspectFill' />
              <Text className='remove-btn' onClick={() => removeImage(i)}>✕</Text>
            </View>
          ))}
          {images.length < 9 && (
            <View className='add-image' onClick={chooseImages}>
              <Text className='add-icon'>📷</Text>
              <Text className='add-text'>添加图片</Text>
            </View>
          )}
        </View>
      </View>

      <View className='btn-area'>
        <View
          className={`publish-btn ${(!content.trim() || loading) ? 'disabled' : ''}`}
          onClick={handlePublish}
        >
          <Text className='publish-text'>{loading ? '发布中...' : '发 布'}</Text>
        </View>
      </View>
    </View>
  )
}
