import { redirect } from "next/navigation"

export default function SprintBoardRedirect({ params }: { params: { id: string } }) {
  redirect(`/projects/${params.id}/execution`)
}
