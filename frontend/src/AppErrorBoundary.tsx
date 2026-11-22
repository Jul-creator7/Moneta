import { Component, type ReactNode } from "react"
import { Button } from "./components/ui/button"

export class AppErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <main className="status-screen">
        <p role="alert">Moneta ran into a problem while displaying this page.</p>
        <Button onClick={() => window.location.reload()}>Reload page</Button>
      </main>
    )
  }
}
