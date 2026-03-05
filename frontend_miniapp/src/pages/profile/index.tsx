import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { useState } from 'react'
import api, { clearToken } from '../../utils/request'
import './index.scss'

interface UserInfo {
  id: number
  phone: string
  nickname: string
  avatar_url: string | null
  created_at: string
}

export default function Profile() {
  const [user, setUser] = useState<UserInfo | null>(null)
  const [petCount, setPetCount] = useState(0)
  const [diaryCount, setDiaryCount] = useState(0)

  useDidShow(() => {
    loadUser()
  })

  const loadUser = async () => {
    try {
      const me = await api.get<UserInfo>('/users/me')
      setUser(me)

      // 加载统计
      const pets = await api.get<any[]>('/pets/mine')
      setPetCount(pets.length)

      // 粗略统计日记数：取第一只宠物的日记
      if (pets.length > 0) {
        const diaries = await api.get<any[]>(`/diary/${pets[0].id}?limit=999`)
        setDiaryCount(diaries.length)
      }
    } catch {}
  }

  const menuItems = [
    {
      icon: '🐾', label: '我的宠物档案', desc: '管理宠物基本信息',
      action: () => Taro.navigateTo({ url: '/pages/pet-edit/index' }),
    },
    {
      icon: '📋', label: '就诊记录', desc: '疫苗、驱虫、就医历史',
      action: () => {
        // 跳转到日记页，未来可做专门的就诊记录列表页
        Taro.showToast({ title: '功能开发中', icon: 'none' })
      },
    },
    {
      icon: '📔', label: '健康日记', desc: '查看历史打卡记录',
      action: async () => {
        const pets = await api.get<any[]>('/pets/mine')
        if (pets.length > 0) {
          Taro.navigateTo({ url: `/pages/diary/index?petId=${pets[0].id}&petName=${pets[0].name}` })
        } else {
          Taro.showToast({ title: '请先添加宠物', icon: 'none' })
        }
      },
    },
    {
      icon: '🏥', label: '附近宠物医院', desc: '24小时急诊导航',
      action: () => Taro.showToast({ title: '功能开发中', icon: 'none' }),
    },
    {
      icon: '⚙️', label: '退出登录', desc: '清除登录状态',
      action: () => {
        Taro.showModal({
          title: '确认退出',
          content: '退出后需要重新登录',
          success: (res) => {
            if (res.confirm) {
              clearToken()
              Taro.removeStorageSync('userId')
              Taro.removeStorageSync('nickname')
              Taro.redirectTo({ url: '/pages/login/index' })
            }
          },
        })
      },
    },
  ]

  return (
    <ScrollView className='profile' scrollY>
      {/* 用户信息卡 */}
      <View className='profile-hero'>
        <View className='profile-avatar'>
          <Text style={{ fontSize: '40px' }}>🧑</Text>
        </View>
        <Text className='profile-name'>{user?.nickname || '加载中...'}</Text>
        <View className='profile-stats'>
          <View className='stat-item'>
            <Text className='stat-num'>{petCount}</Text>
            <Text className='stat-label'>宠物</Text>
          </View>
          <View className='stat-divider' />
          <View className='stat-item'>
            <Text className='stat-num'>{diaryCount}</Text>
            <Text className='stat-label'>打卡天数</Text>
          </View>
          <View className='stat-divider' />
          <View className='stat-item'>
            <Text className='stat-num'>{user?.phone?.slice(-4) || '--'}</Text>
            <Text className='stat-label'>尾号</Text>
          </View>
        </View>
      </View>

      {/* 菜单列表 */}
      <View className='menu-section'>
        {menuItems.map(item => (
          <View key={item.label} className='menu-item' onClick={item.action}>
            <Text className='menu-icon'>{item.icon}</Text>
            <View className='menu-body'>
              <Text className='menu-label'>{item.label}</Text>
              <Text className='menu-desc'>{item.desc}</Text>
            </View>
            <Text className='menu-arrow'>›</Text>
          </View>
        ))}
      </View>

      <Text className='version-text'>宠物阿福 v0.1.0 · 由 AI 驱动</Text>
    </ScrollView>
  )
}
