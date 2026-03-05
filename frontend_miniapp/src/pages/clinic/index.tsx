import { View, Text, ScrollView, Input, Image } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useState, useRef } from 'react'
import { API_V1 } from '../../config'
import { getToken } from '../../utils/request'
import './index.scss'

interface Message {
  id: number
  role: 'user' | 'ai'
  content: string
  image?: string
}

let msgIdCounter = 0

export default function Clinic() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: msgIdCounter++,
      role: 'ai',
      content: '你好！我是宠物阿福AI助手 🐾\n我可以帮你分析宠物的症状表现，参考兽医学术文献给出建议。\n\n**请注意：** 我的回复仅供参考，不能代替执业兽医的专业诊断。',
    },
  ])
  const [inputText, setInputText] = useState('')
  const [loading, setLoading] = useState(false)
  const [pendingImage, setPendingImage] = useState<{ path: string; base64: string } | null>(null)
  const scrollRef = useRef<any>(null)

  const chooseImage = async () => {
    try {
      const res = await Taro.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera'],
      })
      const path = res.tempFilePaths[0]
      const fsm = Taro.getFileSystemManager()
      fsm.readFile({
        filePath: path,
        encoding: 'base64',
        success: (r) => {
          setPendingImage({ path, base64: r.data as string })
        },
        fail: () => Taro.showToast({ title: '图片读取失败', icon: 'error' }),
      })
    } catch {
      // 用户取消
    }
  }

  const sendMessage = async () => {
    const text = inputText.trim()
    if (!text && !pendingImage) return
    if (loading) return

    // 检查登录状态
    const token = getToken()
    if (!token) {
      Taro.showToast({ title: '请先登录', icon: 'none' })
      Taro.redirectTo({ url: '/pages/login/index' })
      return
    }

    const userMsg: Message = {
      id: msgIdCounter++,
      role: 'user',
      content: text || '（已上传图片，请分析）',
      image: pendingImage?.path,
    }
    setMessages(prev => [...prev, userMsg])
    setInputText('')
    const imgB64 = pendingImage?.base64 || null
    setPendingImage(null)
    setLoading(true)

    const aiMsgId = msgIdCounter++
    setMessages(prev => [...prev, { id: aiMsgId, role: 'ai', content: '' }])

    try {
      const endpoint = imgB64
        ? `${API_V1}/diagnosis/image`
        : `${API_V1}/diagnosis/text`

      const authHeader = { Authorization: `Bearer ${token}` }

      if (process.env.TARO_ENV === 'weapp') {
        // 微信小程序 — 流式
        const task = Taro.request({
          url: endpoint,
          method: 'POST',
          data: imgB64
            ? { symptom: text, image_base64: imgB64 }
            : { symptom: text },
          header: {
            'Content-Type': 'application/x-www-form-urlencoded',
            ...authHeader,
          },
          enableChunked: true,
          success: () => {},
        } as any)

        ;(task as any).onChunkReceived?.((res: any) => {
          const decoder = new TextDecoder('utf-8')
          const chunk = decoder.decode(res.data)
          const lines = chunk.split('\n').filter(l => l.startsWith('data: '))
          lines.forEach(line => {
            const content = line.slice(6)
            if (content === '[DONE]') {
              setLoading(false)
              return
            }
            setMessages(prev =>
              prev.map(m => m.id === aiMsgId ? { ...m, content: m.content + content } : m)
            )
          })
        })
      } else {
        // H5 — fetch SSE
        const resp = await fetch(endpoint, {
          method: 'POST',
          headers: authHeader,
          body: (() => {
            const fd = new FormData()
            fd.append('symptom', text || '请分析此图片')
            return fd
          })(),
        })

        if (resp.status === 401) {
          Taro.showToast({ title: '登录已过期', icon: 'none' })
          Taro.redirectTo({ url: '/pages/login/index' })
          return
        }

        const reader = resp.body!.getReader()
        const decoder = new TextDecoder()
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          const raw = decoder.decode(value)
          const lines = raw.split('\n').filter(l => l.startsWith('data: '))
          for (const line of lines) {
            const content = line.slice(6)
            if (content === '[DONE]') break
            setMessages(prev =>
              prev.map(m => m.id === aiMsgId ? { ...m, content: m.content + content } : m)
            )
          }
        }
      }
    } catch (e: any) {
      setMessages(prev =>
        prev.map(m => m.id === aiMsgId ? { ...m, content: `❌ 请求失败：${e.message || '网络错误'}` } : m)
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <View className='clinic'>
      <ScrollView
        className='msg-list'
        scrollY
        scrollIntoView={`msg-${messages[messages.length - 1]?.id}`}
      >
        {messages.map(msg => (
          <View
            key={msg.id}
            id={`msg-${msg.id}`}
            className={`msg-row ${msg.role}`}
          >
            {msg.role === 'ai' && (
              <View className='avatar ai-avatar'>🐾</View>
            )}
            <View className='bubble-wrap'>
              {msg.image && (
                <Image
                  className='msg-image'
                  src={msg.image}
                  mode='widthFix'
                />
              )}
              <View className={`bubble ${msg.role}`}>
                {msg.content === '' && loading ? (
                  <View className='typing-dots'>
                    <Text className='dot' />
                    <Text className='dot' />
                    <Text className='dot' />
                  </View>
                ) : (
                  <Text className='bubble-text' userSelect>{msg.content}</Text>
                )}
              </View>
            </View>
            {msg.role === 'user' && (
              <View className='avatar user-avatar'>我</View>
            )}
          </View>
        ))}
      </ScrollView>

      {pendingImage && (
        <View className='pending-image-bar'>
          <Image className='pending-preview' src={pendingImage.path} mode='aspectFill' />
          <Text className='pending-tip'>📷 待发送图片</Text>
          <Text className='pending-remove' onClick={() => setPendingImage(null)}>✕</Text>
        </View>
      )}

      <View className='input-bar'>
        <View className='img-btn' onClick={chooseImage}>
          <Text>📷</Text>
        </View>
        <Input
          className='text-input'
          value={inputText}
          onInput={e => setInputText(e.detail.value)}
          placeholder='描述症状，或上传图片...'
          confirm-type='send'
          onConfirm={sendMessage}
          adjustPosition
        />
        <View
          className={`send-btn ${(!inputText.trim() && !pendingImage) || loading ? 'disabled' : ''}`}
          onClick={sendMessage}
        >
          <Text>发送</Text>
        </View>
      </View>
    </View>
  )
}
