import { View, Text, ScrollView, Slider, Textarea, Switch } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import { useState, useEffect } from 'react'
import api from '../../utils/request'
import './index.scss'

interface DiaryEntry {
  id: number
  pet_id: number
  appetite_score: number | null
  energy_score: number | null
  stool_normal: boolean | null
  notes: string | null
  recorded_at: string
}

const SCORE_LABELS = ['', '很差', '较差', '一般', '良好', '很棒']
const SCORE_EMOJIS = ['', '😢', '😟', '😐', '😊', '🤩']

export default function Diary() {
  const router = useRouter()
  const petId = Number(router.params.petId || 0)
  const petName = router.params.petName || '宠物'

  const [appetite, setAppetite] = useState(3)
  const [energy, setEnergy] = useState(3)
  const [stoolNormal, setStoolNormal] = useState(true)
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState<DiaryEntry[]>([])
  const [showHistory, setShowHistory] = useState(false)

  useEffect(() => {
    if (petId) loadHistory()
  }, [petId])

  const loadHistory = async () => {
    try {
      const list = await api.get<DiaryEntry[]>(`/diary/${petId}?limit=7`)
      setHistory(list)
    } catch {}
  }

  const handleSubmit = async () => {
    if (!petId) {
      Taro.showToast({ title: '请先选择宠物', icon: 'none' })
      return
    }
    setLoading(true)
    try {
      const userId = Taro.getStorageSync('userId')
      const res = await api.post('/diary/', {
        user_id: userId,
        pet_id: petId,
        appetite_score: appetite,
        energy_score: energy,
        stool_normal: stoolNormal,
        notes: notes.trim() || null,
      })
      // 检查食欲不振预警
      if (res._alert) {
        Taro.showModal({
          title: '⚠️ 健康预警',
          content: res._alert,
          confirmText: '知道了',
          showCancel: false,
        })
      } else {
        Taro.showToast({ title: '打卡成功 ✅', icon: 'success' })
      }
      setNotes('')
      loadHistory()
    } catch {
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (iso: string) => {
    const d = new Date(iso)
    return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
  }

  return (
    <ScrollView className='diary' scrollY>
      {/* 标题 */}
      <View className='diary-header'>
        <Text className='diary-title'>📝 {petName}的健康日记</Text>
        <Text className='diary-sub'>记录今天的状态吧</Text>
      </View>

      {/* 打卡表单 */}
      <View className='diary-card'>
        {/* 食欲 */}
        <View className='score-section'>
          <View className='score-header'>
            <Text className='score-label'>🍖 食欲</Text>
            <Text className='score-value'>{SCORE_EMOJIS[appetite]} {SCORE_LABELS[appetite]}</Text>
          </View>
          <Slider
            min={1} max={5} step={1} value={appetite}
            activeColor='#4CAF50' blockColor='#4CAF50'
            onChange={e => setAppetite(e.detail.value)}
          />
        </View>

        {/* 精神 */}
        <View className='score-section'>
          <View className='score-header'>
            <Text className='score-label'>😺 精神</Text>
            <Text className='score-value'>{SCORE_EMOJIS[energy]} {SCORE_LABELS[energy]}</Text>
          </View>
          <Slider
            min={1} max={5} step={1} value={energy}
            activeColor='#4CAF50' blockColor='#4CAF50'
            onChange={e => setEnergy(e.detail.value)}
          />
        </View>

        {/* 排便 */}
        <View className='stool-section'>
          <Text className='score-label'>🚽 排便正常</Text>
          <Switch checked={stoolNormal} onChange={e => setStoolNormal(e.detail.value)} color='#4CAF50' />
        </View>

        {/* 备注 */}
        <Textarea
          className='notes-input'
          placeholder='备注（选填）：今天有什么特别的？'
          value={notes}
          onInput={e => setNotes(e.detail.value)}
          maxlength={200}
        />

        {/* 提交 */}
        <View
          className={`submit-btn ${loading ? 'disabled' : ''}`}
          onClick={handleSubmit}
        >
          <Text className='submit-text'>{loading ? '提交中...' : '✅ 完成打卡'}</Text>
        </View>
      </View>

      {/* 历史记录 */}
      {history.length > 0 && (
        <View className='history-section'>
          <View className='history-header' onClick={() => setShowHistory(!showHistory)}>
            <Text className='history-title'>📅 最近7天记录</Text>
            <Text className='history-toggle'>{showHistory ? '收起 ▲' : '展开 ▼'}</Text>
          </View>
          {showHistory && history.map(entry => (
            <View key={entry.id} className='history-item'>
              <Text className='history-date'>{formatDate(entry.recorded_at)}</Text>
              <View className='history-scores'>
                <Text>🍖{SCORE_LABELS[entry.appetite_score || 3]}</Text>
                <Text>😺{SCORE_LABELS[entry.energy_score || 3]}</Text>
                <Text>🚽{entry.stool_normal === false ? '异常' : '正常'}</Text>
              </View>
              {entry.notes && <Text className='history-notes'>{entry.notes}</Text>}
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  )
}
