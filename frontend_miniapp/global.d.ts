/// <reference types="@tarojs/taro" />

declare namespace NodeJS {
  interface ProcessEnv {
    readonly TARO_ENV: "weapp" | "swan" | "alipay" | "h5" | "rn";
    readonly NODE_ENV: "development" | "production";
  }
}
