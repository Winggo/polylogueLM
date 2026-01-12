import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import { AntdRegistry } from '@ant-design/nextjs-registry'
import '@xyflow/react/dist/base.css'
import "./globals.css"


const geistSans = Geist({
    variable: "--font-geist-sans",
    subsets: ["latin"],
})

const geistMono = Geist_Mono({
    variable: "--font-geist-mono",
    subsets: ["latin"],
})

export const metadata: Metadata = {
    title: "Polylogue",
    description: "Enable parallel LLM dialogs",
    icons: {
        icon: '/favicon.ico',
    },
}

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode
}>) {
    return (
        <html lang="en">
            <head>
                <link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600&display=swap" rel="stylesheet"/>
            </head>
            <body
                className={`${geistSans.variable} ${geistMono.variable} antialiased`}
            >
                <AntdRegistry>
                    {children}
                </AntdRegistry>
            </body>
        </html>
    )
}
