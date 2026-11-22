import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router-dom"
import { App } from "./App"
import { AppErrorBoundary } from "./AppErrorBoundary"
import { AuthProvider } from "./auth"
import "./styles.css"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AppErrorBoundary><AuthProvider><App /></AuthProvider></AppErrorBoundary>
    </BrowserRouter>
  </StrictMode>,
)
