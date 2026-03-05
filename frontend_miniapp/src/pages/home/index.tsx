import { View, Text, Image, ScrollView } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { useState } from 'react'
import api from '../../utils/request'
import './index.scss'

interface Pet {
  id: number
  name: string
  species: string
  breed: string | null
  gender: string
  birth_date: string | null
  weight_kg: number | null
  is_neutered: boolean
  avatar_url: string | null
}

interface Reminder {
  id: number
  icon: string
  text: string
  date: string
  urgent: boolean
}

interface DiaryEntry {
  appetite_score: number | null
  energy_score: number | null
  stool_normal: boolean | null
}

const SPECIES_MAP: Record<string, string> = { cat: '猫', dog: '狗', other: '其他' }
const SCORE_LABELS = ['', '很差', '较差', '一般', '良好', '很棒']

export default function Home() {
  const [pet, setPet] = useState<Pet | null>(null)
  const [pets, setPets] = useState<Pet[]>([])
  const [reminders, setReminders] = useState<Reminder[]>([])
  const [todayDiary, setTodayDiary] = useState<DiaryEntry | null>(null)
  const [loading, setLoading] = useState(true)

  // 每次页面显示时刷新（从其他Tab切回、添加宠物后）
  useDidShow(() => {
    loadData()
  })

  const loadData = async () => {
    setLoading(true)
    try {
      const petList = await api.get<Pet[]>('/pets/mine')
      setPets(petList)

      if (petList.length > 0) {
        const mainPet = petList[0]
        setPet(mainPet)

        // 加载最近日记
        try {
          const diaryList = await api.get<any[]>(`/diary/${mainPet.id}?limit=1`)
          if (diaryList.length > 0) {
            setTodayDiary(diaryList[0])
          }
        } catch {}

        // 加载就诊记录提醒
        try {
          const records = await api.get<any[]>(`/medical-records/${mainPet.id}`)
          const now = new Date()
          const upcoming: Reminder[] = records
            .filter(r => r.next_due_date)
            .map(r => {
              const due = new Date(r.next_due_date)
              const daysLeft = Math.ceil((due.getTime() - now.getTime()) / (86400000))
              return {
                id: r.id,
                icon: r.record_type === 'vaccine' ? '💉' : r.record_type === 'deworming' ? '🐛' : '📋',
                text: r.title,
                date: daysLeft <= 0 ? '已过期' : `${daysLeft}天后到期`,
                urgent: daysLeft <= 7,
              }
            })
            .sort((a, b) => a.urgent === b.urgent ? 0 : a.urgent ? -1 : 1)
            .slice(0, 5)
          setReminders(upcoming)
        } catch {}
      }
    } catch {
    } finally {
      setLoading(false)
    }
  }

  const getAge = (birthDate: string | null): string => {
    if (!birthDate) return ''
    const birth = new Date(birthDate)
    const now = new Date()
    const months = (now.getFullYear() - birth.getFullYear()) * 12 + (now.getMonth() - birth.getMonth())
    if (months < 12) return `${months}个月`
    const years = Math.floor(months / 12)
    const remainder = months % 12
    return remainder > 0 ? `${years}岁${remainder}月` : `${years}岁`
  }

  const goToClinic = () => Taro.switchTab({ url: '/pages/clinic/index' })
  const goToDiary = () => {
    if (!pet) {
      Taro.showToast({ title: '请先添加宠物', icon: 'none' })
      return
    }
    Taro.navigateTo({ url: `/pages/diary/index?petId=${pet.id}&petName=${pet.name}` })
  }
  const goToAddPet = () => Taro.navigateTo({ url: '/pages/pet-edit/index' })

  // 无宠物状态
  if (!loading && pets.length === 0) {
    return (
      <View className='home'>
        <View className='hero-card'>
          <View className='pet-info'>
            <Text className='pet-name'>欢迎来到宠物阿福 🐾</Text>
            <Text className='pet-meta'>添加你的第一只宠物吧</Text>
          </View>
        </View>
        <View className='quick-actions'>
          <View className='action-btn primary' onClick={goToAddPet}>
            <Text className='action-icon'>➕</Text>
            <Text className='action-text'>添加宠物</Text>
          </View>
          <View className='action-btn secondary' onClick={goToClinic}>
            <Text className='action-icon'>💬</Text>
            <Text className='action-text'>AI 咨询</Text>
          </View>
        </View>
      </View>
    )
  }

  return (
    <ScrollView className='home' scrollY>
      {/* 顶部宠物档案卡片 */}
      <View className='hero-card'>
        <View className='pet-avatar-wrap'>
          <Image
            className='pet-avatar'
            src={pet?.avatar_url || `https://api.dicebear.com/7.x/adventurer/svg?seed=${pet?.name || 'pet'}`}
            mode='aspectFill'
          />
          <View className='pet-status-dot' />
        </View>
        <View className='pet-info'>
          <Text className='pet-name'>{pet?.name}</Text>
          <Text className='pet-meta'>
            {pet?.breed || SPECIES_MAP[pet?.species || ''] || ''}
            {pet?.birth_date ? ` · ${getAge(pet.birth_date)}` : ''}
            {pet?.weight_kg ? ` · ${pet.weight_kg}kg` : ''}
          </Text>
        </View>
        <View className='health-score'>
          <Text className='score-num'>{pets.length}</Text>
          <Text className='score-label'>宠物数</Text>
        </View>
      </View>

      {/* 快捷操作区 */}
      <View className='quick-actions'>
        <View className='action-btn primary' onClick={goToClinic}>
          <Text className='action-icon'>📷</Text>
          <Text className='action-text'>拍照问诊</Text>
        </View>
        <View className='action-btn secondary' onClick={goToClinic}>
          <Text className='action-icon'>💬</Text>
          <Text className='action-text'>描述症状</Text>
        </View>
        <View className='action-btn tertiary' onClick={goToDiary}>
          <Text className='action-icon'>📝</Text>
          <Text className='action-text'>写日记</Text>
        </View>
      </View>

      {/* 待办提醒 */}
      {reminders.length > 0 && (
        <View className='section'>
          <Text className='section-title'>📅 近期待办</Text>
          {reminders.map(r => (
            <View key={r.id} className={`reminder-item ${r.urgent ? 'urgent' : ''}`}>
              <Text className='reminder-icon'>{r.icon}</Text>
              <View className='reminder-body'>
                <Text className='reminder-name'>{r.text}</Text>
                <Text className='reminder-date'>{r.date}</Text>
              </View>
              {r.urgent && <Text className='reminder-tag'>⚡ 紧急</Text>}
            </View>
          ))}
        </View>
      )}

      {/* 今日健康打卡 */}
      <View className='section'>
        <Text className='section-title'>🌟 今日健康打卡</Text>
        <View className='checkin-row' onClick={goToDiary}>
          {[
            {
              label: '食欲', emoji: '🍖',
              status: todayDiary ? SCORE_LABELS[todayDiary.appetite_score || 3] : '去打卡',
            },
            {
              label: '精神', emoji: '😺',
              status: todayDiary ? SCORE_LABELS[todayDiary.energy_score || 3] : '去打卡',
            },
            {
              label: '排便', emoji: '🚽',
              status: todayDiary ? (todayDiary.stool_normal === false ? '异常' : '正常') : '去打卡',
            },
          ].map(item => (
            <View key={item.label} className='checkin-item'>
              <Text className='checkin-emoji'>{item.emoji}</Text>
              <Text className='checkin-label'>{item.label}</Text>
              <Text className='checkin-status'>{item.status}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* 多宠物切换提示 */}
      {pets.length > 1 && (
        <View className='section'>
          <Text className='section-title'>🐾 我的宠物 ({pets.length})</Text>
          {pets.map(p => (
            <View
              key={p.id}
              className={`reminder-item ${p.id === pet?.id ? 'urgent' : ''}`}
              onClick={() => setPet(p)}
            >
              <Text className='reminder-icon'>{p.species === 'cat' ? '🐱' : p.species === 'dog' ? '🐶' : '🐾'}</Text>
              <View className='reminder-body'>
                <Text className='reminder-name'>{p.name}</Text>
                <Text className='reminder-date'>{p.breed || SPECIES_MAP[p.species] || ''}</Text>
              </View>
              {p.id === pet?.id && <Text className='reminder-tag'>当前</Text>}
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  )
}
