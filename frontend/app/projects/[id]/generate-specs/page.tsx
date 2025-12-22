"use client"

import { useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { LoadingState } from "@/components/ui/loading-state"

export default function GenerateSpecsPage() {
  const params = useParams()
  const router = useRouter()
  const idValue = params.id
  const projectId = Array.isArray(idValue) ? idValue[0] : idValue

  useEffect(() => {
    if (projectId) {
      router.replace(`/projects/${projectId}?wizard=generate-specs`)
    }
  }, [projectId, router])

  return <LoadingState message="Opening SpecKit wizard..." />
}
