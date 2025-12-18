"use client"

import type React from "react"

import { useEffect } from "react"
import { useRouter, usePathname } from "next/navigation"
import { useAuth } from "./context"
import { LoadingState } from "@/components/ui/loading-state"

interface AuthGuardProps {
  children: React.ReactNode
}

export function AuthGuard({ children }: AuthGuardProps) {
  const { isAuthenticated, isLoading } = useAuth()
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    if (!isLoading && !isAuthenticated && pathname !== "/login") {
      router.push(`/login?redirect=${encodeURIComponent(pathname)}`)
    }
    // </CHANGE>
  }, [isAuthenticated, isLoading, pathname, router])

  if (isLoading) {
    return <LoadingState message="Authenticating..." />
  }

  if (!isAuthenticated && pathname !== "/login") {
    return null
  }

  return <>{children}</>
}
