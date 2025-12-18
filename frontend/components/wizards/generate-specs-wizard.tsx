"use client"

import { useState } from "react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent } from "@/components/ui/card"
import { ArrowRight, CheckCircle2, Sparkles } from "lucide-react"
import { toast } from "sonner"

interface GenerateSpecsWizardProps {
  projectId: number
  open: boolean
  onClose: () => void
}

export function GenerateSpecsWizard({ projectId, open, onClose }: GenerateSpecsWizardProps) {
  const [step, setStep] = useState(1)
  const [formData, setFormData] = useState({
    featureName: "",
    featureDescription: "",
    techStack: "",
    requirements: "",
    constraints: "",
  })

  const handleNext = () => {
    if (step < 3) setStep(step + 1)
  }

  const handleBack = () => {
    if (step > 1) setStep(step - 1)
  }

  const handleGenerate = async () => {
    try {
      // Simulate spec generation
      await new Promise((resolve) => setTimeout(resolve, 2000))
      toast.success("Specification generated successfully!")
      onClose()
      setStep(1)
    } catch (err) {
      toast.error("Failed to generate specification")
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-purple-500" />
            Generate Specification Wizard
          </DialogTitle>
          <DialogDescription>AI-powered specification generation for your feature</DialogDescription>
        </DialogHeader>

        <div className="flex items-center justify-between mb-6">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center">
              <div
                className={`flex items-center justify-center w-8 h-8 rounded-full ${
                  s <= step ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                }`}
              >
                {s < step ? <CheckCircle2 className="h-5 w-5" /> : s}
              </div>
              {s < 3 && <div className={`w-20 h-0.5 mx-2 ${s < step ? "bg-primary" : "bg-muted"}`} />}
            </div>
          ))}
        </div>

        <div className="py-4">
          {step === 1 && (
            <div className="space-y-4">
              <div>
                <h3 className="font-semibold mb-4">Feature Information</h3>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="featureName">Feature Name</Label>
                    <Input
                      id="featureName"
                      placeholder="e.g., User Authentication System"
                      value={formData.featureName}
                      onChange={(e) => setFormData({ ...formData, featureName: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="featureDescription">Description</Label>
                    <Textarea
                      id="featureDescription"
                      placeholder="Describe what this feature should do..."
                      rows={4}
                      value={formData.featureDescription}
                      onChange={(e) => setFormData({ ...formData, featureDescription: e.target.value })}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div>
                <h3 className="font-semibold mb-4">Technical Details</h3>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="techStack">Tech Stack</Label>
                    <Input
                      id="techStack"
                      placeholder="e.g., Next.js, PostgreSQL, Redis"
                      value={formData.techStack}
                      onChange={(e) => setFormData({ ...formData, techStack: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="requirements">Functional Requirements</Label>
                    <Textarea
                      id="requirements"
                      placeholder="List the key requirements..."
                      rows={4}
                      value={formData.requirements}
                      onChange={(e) => setFormData({ ...formData, requirements: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="constraints">Constraints</Label>
                    <Textarea
                      id="constraints"
                      placeholder="Any technical or business constraints..."
                      rows={3}
                      value={formData.constraints}
                      onChange={(e) => setFormData({ ...formData, constraints: e.target.value })}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <div>
                <h3 className="font-semibold mb-4">Review & Generate</h3>
                <Card>
                  <CardContent className="pt-6 space-y-3">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Feature</p>
                      <p className="font-medium">{formData.featureName}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Tech Stack</p>
                      <p className="text-sm">{formData.techStack || "Not specified"}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Description</p>
                      <p className="text-sm text-muted-foreground">{formData.featureDescription}</p>
                    </div>
                  </CardContent>
                </Card>
                <p className="text-sm text-muted-foreground mt-4">
                  Click "Generate" to create a detailed technical specification using AI.
                </p>
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-between mt-6">
          <Button variant="outline" onClick={step === 1 ? onClose : handleBack}>
            {step === 1 ? "Cancel" : "Back"}
          </Button>
          {step < 3 ? (
            <Button onClick={handleNext}>
              Next
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          ) : (
            <Button onClick={handleGenerate}>
              <Sparkles className="mr-2 h-4 w-4" />
              Generate Specification
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
