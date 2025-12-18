export interface User {
  id: string
  email: string
  name: string
  role: "admin" | "member" | "viewer"
  avatar?: string
  company?: string
  createdAt?: string
}
