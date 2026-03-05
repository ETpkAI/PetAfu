import { View, Text, ScrollView, Image } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { useState } from 'react'
import api from '../../utils/request'
import { API_BASE } from '../../config'
import './index.scss'

interface Author {
  id: number
  nickname: string | null
  avatar_url: string | null
}

interface Post {
  id: number
  author: Author
  content: string
  images: string[]
  like_count: number
  comment_count: number
  liked_by_me: boolean
  created_at: string
}

export default function Community() {
  const [posts, setPosts] = useState<Post[]>([])
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [hasMore, setHasMore] = useState(true)

  useDidShow(() => {
    // 每次进入页面刷新
    refresh()
  })

  const refresh = async () => {
    setLoading(true)
    try {
      const res = await api.get<{ items: Post[]; page: number; size: number }>(
        '/community/posts?page=1&size=20'
      )
      setPosts(res.items)
      setPage(1)
      setHasMore(res.items.length >= 20)
    } catch {} finally {
      setLoading(false)
    }
  }

  const loadMore = async () => {
    if (loading || !hasMore) return
    setLoading(true)
    const nextPage = page + 1
    try {
      const res = await api.get<{ items: Post[] }>(
        `/community/posts?page=${nextPage}&size=20`
      )
      setPosts(prev => [...prev, ...res.items])
      setPage(nextPage)
      setHasMore(res.items.length >= 20)
    } catch {} finally {
      setLoading(false)
    }
  }

  const toggleLike = async (postId: number) => {
    try {
      const res = await api.post<{ action: string; like_count: number }>(
        `/community/posts/${postId}/like`
      )
      setPosts(prev => prev.map(p =>
        p.id === postId
          ? { ...p, like_count: res.like_count, liked_by_me: res.action === 'liked' }
          : p
      ))
    } catch {}
  }

  const getImgUrl = (url: string) => {
    if (url.startsWith('http')) return url
    return `${API_BASE}${url}`
  }

  const formatTime = (iso: string) => {
    const d = new Date(iso)
    const now = new Date()
    const diff = Math.floor((now.getTime() - d.getTime()) / 1000)
    if (diff < 60) return '刚刚'
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
    if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
    if (diff < 604800) return `${Math.floor(diff / 86400)}天前`
    return `${d.getMonth() + 1}/${d.getDate()}`
  }

  return (
    <View className='community'>
      <ScrollView
        className='community-scroll'
        scrollY
        onScrollToLower={loadMore}
        refresherEnabled
        refresherTriggered={loading && page === 1}
        onRefresherRefresh={refresh}
      >
        <View className='community-header'>
          <Text className='header-title'>🐾 宠友圈</Text>
          <Text className='header-sub'>分享你和宠物的故事</Text>
        </View>

        <View className='posts'>
          {posts.length === 0 && !loading && (
            <View className='empty-tip'>
              <Text className='empty-emoji'>📝</Text>
              <Text className='empty-text'>还没有帖子，快来发第一条吧！</Text>
            </View>
          )}
          {posts.map(post => (
            <View key={post.id} className='post-card'>
              <View className='post-header'>
                <View className='post-avatar'>
                  <Text style={{ fontSize: '20px' }}>🧑</Text>
                </View>
                <View className='post-user-info'>
                  <Text className='post-username'>{post.author.nickname || '用户'}</Text>
                  <Text className='post-time'>{formatTime(post.created_at)}</Text>
                </View>
              </View>
              <Text className='post-content' userSelect>{post.content}</Text>
              {post.images.length > 0 && (
                <View className='post-images'>
                  {post.images.map((img, i) => (
                    <Image
                      key={i}
                      className='post-img'
                      src={getImgUrl(img)}
                      mode='aspectFill'
                      onClick={() => {
                        Taro.previewImage({
                          urls: post.images.map(getImgUrl),
                          current: getImgUrl(img),
                        })
                      }}
                    />
                  ))}
                </View>
              )}
              <View className='post-actions'>
                <View
                  className={`action-item ${post.liked_by_me ? 'liked' : ''}`}
                  onClick={() => toggleLike(post.id)}
                >
                  <Text>{post.liked_by_me ? '❤️' : '🤍'}</Text>
                  <Text className='action-count'>{post.like_count || ''}</Text>
                </View>
                <View className='action-item'>
                  <Text>💬</Text>
                  <Text className='action-count'>{post.comment_count || ''}</Text>
                </View>
                <View className='action-item'>
                  <Text>📤</Text>
                  <Text className='action-count'>分享</Text>
                </View>
              </View>
            </View>
          ))}
          {loading && <Text className='loading-text'>加载中...</Text>}
          {!hasMore && posts.length > 0 && (
            <Text className='loading-text'>— 没有更多了 —</Text>
          )}
        </View>
      </ScrollView>

      {/* 发帖浮动按钮 */}
      <View
        className='fab-btn'
        onClick={() => Taro.navigateTo({ url: '/pages/post-create/index' })}
      >
        <Text className='fab-icon'>✍️</Text>
      </View>
    </View>
  )
}
