import { Link } from "react-router-dom";
import { Compass } from "lucide-react";

export default function NotFound() {
  return (
    <div className="empty empty-page">
      <span className="empty-icon" aria-hidden="true"><Compass size={26} /></span>
      <h1>Page not found</h1>
      <p>The page you’re looking for doesn’t exist or has moved.</p>
      <Link className="btn btn-primary" to="/">Go to the start page</Link>
    </div>
  );
}
