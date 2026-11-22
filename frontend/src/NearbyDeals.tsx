import { useCallback, useEffect, useState } from "react"
import { ArrowUpRight, Compass, LocateFixed, MapPin } from "lucide-react"
import { requestError, useAuthenticatedApi } from "./authenticatedApi"
import { financialDate } from "./intelligence"
import { Button } from "./components/ui/button"

type Coordinates = { latitude: number; longitude: number }
type Deal = Coordinates & {
  id: number; store: string; product: string; category: string; city: string; currency: string
  original_minor: number; sale_minor: number; expires_on: string | null
}

const groceryFlyers = [
  { name: "Metro", url: "https://www.metro.ca/en/flyer", cities: ["Montréal", "Laval", "Toronto"] },
  { name: "Super C", url: "https://www.superc.ca/en/flyer", cities: ["Montréal", "Laval"] },
  { name: "Food Basics", url: "https://www.foodbasics.ca/flyer", cities: ["Toronto"] },
]
const NEARBY_KM = 20
const radians = (degrees: number) => degrees * Math.PI / 180

function distance(from: Coordinates, to: Coordinates) {
  const latitude = radians(to.latitude - from.latitude)
  const longitude = radians(to.longitude - from.longitude)
  const square = Math.sin(latitude / 2) ** 2
    + Math.cos(radians(from.latitude)) * Math.cos(radians(to.latitude)) * Math.sin(longitude / 2) ** 2
  return 6371 * 2 * Math.asin(Math.sqrt(Math.min(1, square)))
}

export function NearbyDeals({ token, onExpired }: { token: string; onExpired: () => void }) {
  const call = useAuthenticatedApi(token, onExpired)
  const [deals, setDeals] = useState<Deal[]>()
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(true)
  const [category, setCategory] = useState("")
  const [city, setCity] = useState("")
  const [location, setLocation] = useState<Coordinates>()
  const [locating, setLocating] = useState(false)
  const [locationStatus, setLocationStatus] = useState("")

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true)
    setError("")
    try {
      const result = await call<Deal[]>("/deals", { signal })
      if (!signal?.aborted) setDeals(result)
    } catch (failure) {
      if (!signal?.aborted) setError(requestError(failure))
    } finally {
      if (!signal?.aborted) setLoading(false)
    }
  }, [call])

  useEffect(() => {
    const controller = new AbortController()
    void load(controller.signal)
    return () => controller.abort()
  }, [load])

  function useLocation() {
    setLocationStatus("")
    if (!navigator.geolocation) {
      setLocationStatus("Location is unavailable in this browser. You can still browse by city.")
      return
    }
    setLocating(true)
    navigator.geolocation.getCurrentPosition(({ coords }) => {
      setCity("")
      setLocation({ latitude: coords.latitude, longitude: coords.longitude })
      setLocationStatus(`Showing sample offers within ${NEARBY_KM} km.`)
      setLocating(false)
    }, () => {
      setLocationStatus("Location could not be used. You can still browse by city.")
      setLocating(false)
    }, { enableHighAccuracy: false, timeout: 8000, maximumAge: 120000 })
  }

  const cities = [...new Set(deals?.map((deal) => deal.city))].sort()
  const categories = [...new Set(deals?.map((deal) => deal.category))].sort()
  const visible = (deals ?? [])
    .filter((deal) => (!city || deal.city === city) && (!category || deal.category === category))
    .map((deal) => ({ deal, km: location ? distance(location, deal) : undefined }))
    .filter(({ km }) => km === undefined || km <= NEARBY_KM)
    .sort((a, b) => (a.km ?? 0) - (b.km ?? 0))

  return (
    <div className="banking">
      <section className="bank-hero">
        <div>
          <p className="bank-eyebrow"><Compass size={18} aria-hidden /> Simulated deals · CAD</p>
          <h1>Explore nearby deals</h1>
          <p>Browse sample food and clothing offers by city or check for examples near your location.</p>
        </div>
      </section>

      {loading && <p className="bank-feedback" role="status">Loading sample deals…</p>}
      {error && <div className="bank-feedback bank-error" role="alert">{error} <Button onClick={() => void load()}>Retry</Button></div>}
      {deals && <>
        <section className="card">
          <h2>Filter sample offers</h2>
          <div className="bank-form">
            <div className="bank-fields">
              <label><span id="deal-city">City</span>
                <select aria-labelledby="deal-city" value={city} disabled={locating} onChange={(event) => {
                  setCity(event.target.value)
                  setLocation(undefined)
                  setLocationStatus("")
                }}>
                  <option value="">All demo cities</option>
                  {cities.map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>
              <label><span id="deal-category">Category</span>
                <select aria-labelledby="deal-category" value={category} onChange={(event) => setCategory(event.target.value)}>
                  <option value="">All categories</option>
                  {categories.map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>
            </div>
          </div>
          <div className="bank-actions">
            <Button className="bank-secondary" disabled={locating} onClick={useLocation}>
              <LocateFixed size={17} aria-hidden /> {locating ? "Finding location…" : "Use my location"}
            </Button>
            {location && <Button className="bank-secondary" disabled={locating} onClick={() => {
              setLocation(undefined)
              setLocationStatus("")
            }}>Clear location</Button>}
          </div>
          <p>Distance is calculated in this browser. Your location is only used while this page is open.</p>
          {locationStatus && <p role="status">{locationStatus}</p>}
        </section>

        <section className="deal-section" aria-labelledby="deal-heading">
          <h2 id="deal-heading">Demo offers</h2>
          <p>These sample prices illustrate potential savings and cannot be redeemed.</p>
          {visible.length === 0 ? <p className="bank-empty">No demo offers match these filters. Choose another category or browse all demo cities.</p> : (
            <div className="deal-grid">
              {visible.map(({ deal, km }) => <DealCard deal={deal} km={km} key={deal.id} />)}
            </div>
          )}
        </section>

        <section className="card">
          <h2>Official grocery flyers</h2>
          <p>Try these experimental source links to discover current offers. Select your store on the retailer’s site to check prices and availability.</p>
          <ul className="flyer-list">
            {groceryFlyers.filter((flyer) => !city || flyer.cities.includes(city)).map((flyer) => (
              <li key={flyer.name}>
                <a href={flyer.url} target="_blank" rel="noreferrer">{flyer.name} flyer <ArrowUpRight size={17} aria-hidden /><span className="sr-only"> (opens in a new tab)</span></a>
                <p>{flyer.cities.join(", ")}</p>
              </li>
            ))}
          </ul>
        </section>
      </>}
    </div>
  )
}

function DealCard({ deal, km }: { deal: Deal; km?: number }) {
  const price = new Intl.NumberFormat("en-CA", { style: "currency", currency: deal.currency })
  return (
    <article className="card deal-card">
      <p>{deal.category} · {deal.store}</p>
      <h3>{deal.product}</h3>
      <p className="deal-location"><MapPin size={16} aria-hidden /> {deal.city}{km === undefined ? "" : ` · ${km.toFixed(1)} km`}</p>
      <div className="deal-prices">
        <strong>{price.format(deal.sale_minor / 100)}</strong>
        <del aria-label={`Original price ${price.format(deal.original_minor / 100)}`}>{price.format(deal.original_minor / 100)}</del>
      </div>
      <p className="bank-positive">Save {price.format((deal.original_minor - deal.sale_minor) / 100)}</p>
      {deal.expires_on && <p>Demo expiry {financialDate(deal.expires_on)}</p>}
    </article>
  )
}
