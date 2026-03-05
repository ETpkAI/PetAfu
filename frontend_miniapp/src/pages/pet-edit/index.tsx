import { View, Text, Input, Picker, Switch } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import { useState, useEffect } from 'react'
import api from '../../utils/request'
import './index.scss'

const SPECIES_OPTIONS = ['cat', 'dog', 'other']
const SPECIES_LABELS = ['🐱 猫', '🐶 狗', '🐾 其他']
const GENDER_OPTIONS = ['male', 'female', 'unknown']
const GENDER_LABELS = ['♂ 公', '♀ 母', '未知']

interface PetData {
  id?: number
  name: string
  species: string
  breed: string
  gender: string
  birth_date: string
  weight_kg: string
  is_neutered: boolean
}

const EMPTY_PET: PetData = {
  name: '',
  species: 'cat',
  breed: '',
  gender: 'unknown',
  birth_date: '',
  weight_kg: '',
  is_neutered: false,
}

export default function PetEdit() {
  const router = useRouter()
  const petId = router.params.petId ? Number(router.params.petId) : null
  const isEdit = !!petId

  const [pet, setPet] = useState<PetData>({ ...EMPTY_PET })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isEdit) {
      loadPet()
    }
  }, [petId])

  const loadPet = async () => {
    try {
      const list = await api.get<any[]>('/pets/mine')
      const found = list.find(p => p.id === petId)
      if (found) {
        setPet({
          id: found.id,
          name: found.name || '',
          species: found.species || 'cat',
          breed: found.breed || '',
          gender: found.gender || 'unknown',
          birth_date: found.birth_date ? found.birth_date.slice(0, 10) : '',
          weight_kg: found.weight_kg ? String(found.weight_kg) : '',
          is_neutered: found.is_neutered || false,
        })
      }
    } catch {}
  }

  const handleSave = async () => {
    if (!pet.name.trim()) {
      Taro.showToast({ title: '请填写宠物名字', icon: 'none' })
      return
    }

    setLoading(true)
    try {
      const body: any = {
        name: pet.name.trim(),
        species: pet.species,
        gender: pet.gender,
        is_neutered: pet.is_neutered,
      }
      if (pet.breed.trim()) body.breed = pet.breed.trim()
      if (pet.birth_date) body.birth_date = pet.birth_date
      if (pet.weight_kg) body.weight_kg = parseFloat(pet.weight_kg)

      if (isEdit) {
        await api.patch(`/pets/${petId}`, body)
        Taro.showToast({ title: '更新成功', icon: 'success' })
      } else {
        await api.post('/pets/', body)
        Taro.showToast({ title: '添加成功', icon: 'success' })
      }

      setTimeout(() => Taro.navigateBack(), 500)
    } catch {
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = () => {
    if (!isEdit) return
    Taro.showModal({
      title: '确认删除',
      content: `确定要删除 ${pet.name} 的档案吗？此操作不可恢复。`,
      confirmColor: '#e53935',
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.delete(`/pets/${petId}`)
            Taro.showToast({ title: '已删除', icon: 'success' })
            setTimeout(() => Taro.navigateBack(), 500)
          } catch {}
        }
      },
    })
  }

  const update = (field: keyof PetData, value: any) => {
    setPet(prev => ({ ...prev, [field]: value }))
  }

  return (
    <View className='pet-edit'>
      <View className='pe-header'>
        <Text className='pe-title'>{isEdit ? '编辑宠物档案' : '添加新宠物'}</Text>
      </View>

      <View className='form-card'>
        {/* 名字 */}
        <View className='form-row'>
          <Text className='form-label'>名字</Text>
          <Input
            className='form-input'
            placeholder='宠物名字'
            value={pet.name}
            onInput={e => update('name', e.detail.value)}
            maxlength={16}
          />
        </View>

        {/* 物种 */}
        <View className='form-row'>
          <Text className='form-label'>物种</Text>
          <Picker
            mode='selector'
            range={SPECIES_LABELS}
            value={SPECIES_OPTIONS.indexOf(pet.species)}
            onChange={e => update('species', SPECIES_OPTIONS[Number(e.detail.value)])}
          >
            <Text className='picker-text'>
              {SPECIES_LABELS[SPECIES_OPTIONS.indexOf(pet.species)]} ▼
            </Text>
          </Picker>
        </View>

        {/* 品种 */}
        <View className='form-row'>
          <Text className='form-label'>品种</Text>
          <Input
            className='form-input'
            placeholder='如：英短、金毛'
            value={pet.breed}
            onInput={e => update('breed', e.detail.value)}
            maxlength={32}
          />
        </View>

        {/* 性别 */}
        <View className='form-row'>
          <Text className='form-label'>性别</Text>
          <Picker
            mode='selector'
            range={GENDER_LABELS}
            value={GENDER_OPTIONS.indexOf(pet.gender)}
            onChange={e => update('gender', GENDER_OPTIONS[Number(e.detail.value)])}
          >
            <Text className='picker-text'>
              {GENDER_LABELS[GENDER_OPTIONS.indexOf(pet.gender)]} ▼
            </Text>
          </Picker>
        </View>

        {/* 生日 */}
        <View className='form-row'>
          <Text className='form-label'>生日</Text>
          <Picker
            mode='date'
            value={pet.birth_date || '2023-01-01'}
            start='2000-01-01'
            end='2026-12-31'
            onChange={e => update('birth_date', e.detail.value)}
          >
            <Text className='picker-text'>
              {pet.birth_date || '选择日期'} ▼
            </Text>
          </Picker>
        </View>

        {/* 体重 */}
        <View className='form-row'>
          <Text className='form-label'>体重(kg)</Text>
          <Input
            className='form-input'
            type='digit'
            placeholder='如 4.2'
            value={pet.weight_kg}
            onInput={e => update('weight_kg', e.detail.value)}
          />
        </View>

        {/* 绝育 */}
        <View className='form-row'>
          <Text className='form-label'>已绝育</Text>
          <Switch
            checked={pet.is_neutered}
            onChange={e => update('is_neutered', e.detail.value)}
            color='#4CAF50'
          />
        </View>
      </View>

      {/* 保存按钮 */}
      <View className='btn-area'>
        <View
          className={`save-btn ${loading ? 'disabled' : ''}`}
          onClick={handleSave}
        >
          <Text className='save-text'>
            {loading ? '保存中...' : isEdit ? '保存修改' : '添加宠物'}
          </Text>
        </View>

        {isEdit && (
          <View className='delete-btn' onClick={handleDelete}>
            <Text className='delete-text'>删除档案</Text>
          </View>
        )}
      </View>
    </View>
  )
}
