export function sanitizeNextPath(nextPath: string | undefined): string {
  return nextPath?.startsWith("/") && !nextPath.startsWith("//") ? nextPath : "/";
}
