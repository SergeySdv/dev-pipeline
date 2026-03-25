type ArtifactLike = {
  type?: string | null;
  kind?: string | null;
  size?: number | null;
  bytes?: number | null;
  path?: string | null;
};

export function artifactKind(artifact: ArtifactLike): string {
  return artifact.kind || artifact.type || "unknown";
}

export function artifactBytes(artifact: ArtifactLike): number | null {
  if (artifact.bytes != null) return artifact.bytes;
  if (artifact.size != null) return artifact.size;
  return null;
}

export function artifactPath(artifact: ArtifactLike): string | null {
  return artifact.path || null;
}
