import { View, Text, Input } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useState } from 'react'
import { api, setToken } from '../../utils/request'
import './index.scss'

type Mode = 'login' | 'register'

interface TokenResp {
  access_token: string
  token_type: string
  user_id: number
  nickname: string
  phone: string
}

export default function Login() {
  const [mode, setMode] = useState<Mode>('login')
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [nickname, setNickname] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async () => {
    if (!phone.trim() || !password.trim()) {
      Taro.showToast({ title: '请填写手机号和密码', icon: 'none' })
      return
    }
    if (!/^1[3-9]\d{9}$/.test(phone)) {
      Taro.showToast({ title: '手机号格式不正确', icon: 'none' })
      return
    }
    if (password.length < 6) {
      Taro.showToast({ title: '密码至少6位', icon: 'none' })
      return
    }

    setLoading(true)
    try {
      const endpoint = mode === 'login' ? '/users/login' : '/users/register'
      const body: any = { phone, password }
      if (mode === 'register' && nickname.trim()) {
        body.nickname = nickname.trim()
      }

      const res = await api.post<TokenResp>(endpoint, body)
      setToken(res.access_token)

      // 存储用户基础信息
      Taro.setStorageSync('userId', res.user_id)
      Taro.setStorageSync('nickname', res.nickname)

      Taro.showToast({ title: mode === 'login' ? '登录成功' : '注册成功', icon: 'success' })

      // 跳转首页
      setTimeout(() => {
        Taro.switchTab({ url: '/pages/home/index' })
      }, 500)
    } catch (e: any) {
      // request.ts 已自动 Toast 错误
    } finally {
      setLoading(false)
    }
  }

  return (
    <View className='login-page'>
      {/* Logo 区 */}
      <View className='logo-area'>
        <Text className='logo-emoji'>🐾</Text>
        <Text className='logo-title'>宠物阿福</Text>
        <Text className='logo-sub'>AI 宠物健康管家</Text>
      </View>

      {/* 表单卡片 */}
      <View className='form-card'>
        {/* 模式切换 */}
        <View className='mode-tabs'>
          <View
            className={`tab ${mode === 'login' ? 'active' : ''}`}
            onClick={() => setMode('login')}
          >
            <Text>登录</Text>
          </View>
          <View
            className={`tab ${mode === 'register' ? 'active' : ''}`}
            onClick={() => setMode('register')}
          >
            <Text>注册</Text>
          </View>
        </View>

        {/* 手机号 */}
        <View className='input-group'>
          <Text className='input-icon'>📱</Text>
          <Input
            className='form-input'
            type='number'
            maxlength={11}
            placeholder='手机号'
            value={phone}
            onInput={e => setPhone(e.detail.value)}
          />
        </View>

        {/* 密码 */}
        <View className='input-group'>
          <Text className='input-icon'>🔒</Text>
          <Input
            className='form-input'
            password
            maxlength={32}
            placeholder='密码（至少6位）'
            value={password}
            onInput={e => setPassword(e.detail.value)}
          />
        </View>

        {/* 昵称（仅注册模式） */}
        {mode === 'register' && (
          <View className='input-group'>
            <Text className='input-icon'>😺</Text>
            <Input
              className='form-input'
              maxlength={16}
              placeholder='昵称（选填）'
              value={nickname}
              onInput={e => setNickname(e.detail.value)}
            />
          </View>
        )}

        {/* 提交按钮 */}
        <View
          className={`submit-btn ${loading ? 'disabled' : ''}`}
          onClick={handleSubmit}
        >
          <Text className='submit-text'>
            {loading ? '请稍候...' : mode === 'login' ? '登 录' : '注 册'}
          </Text>
        </View>

        {/* 底部提示 */}
        <View className='footer-tip'>
          <Text className='tip-text'>
            {mode === 'login' ? '还没有账号？' : '已有账号？'}
          </Text>
          <Text
            className='tip-link'
            onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
          >
            {mode === 'login' ? '立即注册' : '去登录'}
          </Text>
        </View>
      </View>

      <Text className='disclaimer'>
        登录即表示您同意《用户协议》和《隐私政策》
      </Text>
    </View>
  )
}
