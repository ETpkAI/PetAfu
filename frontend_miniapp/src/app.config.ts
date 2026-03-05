export default defineAppConfig({
  pages: [
    'pages/home/index',
    'pages/clinic/index',
    'pages/profile/index',
    'pages/community/index',
    'pages/login/index',
    'pages/diary/index',
    'pages/pet-edit/index',
    'pages/post-create/index',
  ],
  window: {
    navigationBarBackgroundColor: '#4CAF50',
    navigationBarTitleText: '宠物阿福',
    navigationBarTextStyle: 'white',
    backgroundColor: '#f8fdf8',
  },
  tabBar: {
    color: '#999',
    selectedColor: '#4CAF50',
    backgroundColor: '#fff',
    borderStyle: 'white',
    list: [
      {
        pagePath: 'pages/home/index',
        text: '首页',
        iconPath: 'assets/icons/home.png',
        selectedIconPath: 'assets/icons/home_active.png',
      },
      {
        pagePath: 'pages/clinic/index',
        text: 'AI问诊',
        iconPath: 'assets/icons/clinic.png',
        selectedIconPath: 'assets/icons/clinic_active.png',
      },
      {
        pagePath: 'pages/community/index',
        text: '宠友圈',
        iconPath: 'assets/icons/community.png',
        selectedIconPath: 'assets/icons/community_active.png',
      },
      {
        pagePath: 'pages/profile/index',
        text: '我的',
        iconPath: 'assets/icons/profile.png',
        selectedIconPath: 'assets/icons/profile_active.png',
      },
    ],
  },
})
