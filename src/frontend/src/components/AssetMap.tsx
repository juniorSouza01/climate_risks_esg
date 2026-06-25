import { CircleMarker, MapContainer, TileLayer, Tooltip } from "react-leaflet";
import type { Asset } from "../api";
import { avg } from "./util";

export function AssetMap({ assets }: { assets: Asset[] }) {
  const pts = assets.filter(
    (a): a is Asset & { latitude: number; longitude: number } =>
      a.latitude != null && a.longitude != null,
  );

  if (pts.length === 0) {
    return <div className="muted">Sem ativos georreferenciados.</div>;
  }

  const center: [number, number] = [
    avg(pts.map((p) => p.latitude)),
    avg(pts.map((p) => p.longitude)),
  ];

  return (
    <div className="map">
      <MapContainer
        center={center}
        zoom={9}
        scrollWheelZoom={false}
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="© OpenStreetMap"
        />
        {pts.map((p) => (
          <CircleMarker
            key={p.asset_sk}
            center={[p.latitude, p.longitude]}
            radius={9}
            pathOptions={{ color: "#38bdf8", fillColor: "#38bdf8", fillOpacity: 0.6 }}
          >
            <Tooltip>
              {(p.name ?? p.asset_type) + " — " + (p.municipality ?? "") + "/" + (p.state ?? "")}
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
