import { CircleMarker, MapContainer, TileLayer, Tooltip } from "react-leaflet";
import type { Asset } from "../api";
import { avg, severityColor } from "./util";

export function AssetMap({
  assets,
  exposureByAsset = {},
}: {
  assets: Asset[];
  exposureByAsset?: Record<number, number>;
}) {
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
        {pts.map((p) => {
          const exposure = exposureByAsset[p.asset_sk];
          const color = exposure == null ? "#38bdf8" : severityColor(exposure * 100);
          return (
            <CircleMarker
              key={p.asset_sk}
              center={[p.latitude, p.longitude]}
              radius={10}
              pathOptions={{ color, fillColor: color, fillOpacity: 0.65 }}
            >
              <Tooltip>
                {(p.name ?? p.asset_type) +
                  " — " +
                  (p.municipality ?? "") +
                  "/" +
                  (p.state ?? "") +
                  (exposure == null ? "" : ` · exposição ${(exposure * 100).toFixed(0)}`)}
              </Tooltip>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}
