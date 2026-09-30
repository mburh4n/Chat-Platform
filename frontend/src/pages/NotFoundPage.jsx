import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="card">
      <h1>Page not found</h1>
      <p>The page you're looking for doesn't exist.</p>
      <Link to="/">Go to the home page</Link>
    </div>
  );
}
