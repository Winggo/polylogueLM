'use client'

import { ConfigProvider, theme as antdTheme } from 'antd'
import { useTheme } from '../context/ThemeContext'

export default function AntdThemeProvider({ children }: { children: React.ReactNode }) {
    const { theme } = useTheme()

    return (
        <ConfigProvider
            theme={{
                algorithm: theme === 'dark' ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
            }}
        >
            {children}
        </ConfigProvider>
    )
}
