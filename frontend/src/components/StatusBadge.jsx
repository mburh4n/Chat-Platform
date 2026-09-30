const LABELS = {
  processing: "Processing",
  ready: "Ready",
  failed: "Failed",
};

export default function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{LABELS[status] ?? status}</span>;
}
