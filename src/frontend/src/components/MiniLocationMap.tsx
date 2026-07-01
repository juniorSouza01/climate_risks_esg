import { CircleMarker, MapContainer, TileLayer, Tooltip } from "react-leaflet";

export function MiniLocationMap({
  lat,
  lon,
  label,
}: {
  lat: number;
  lon: number;
  label?: string | null;
}) {
  return (
    <div className="map-mini">
      <MapContainer
        center={[lat, lon]}
        zoom={13}
        scrollWheelZoom={false}
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="© OpenStreetMap"
        />
        <CircleMarker
          center={[lat, lon]}
          radius={9}
          pathOptions={{ color: "#38bdf8", fillColor: "#38bdf8", fillOpacity: 0.7 }}
        >
          {label ? <Tooltip>{label}</Tooltip> : null}
        </CircleMarker>
      </MapContainer>
    </div>
  );
}
