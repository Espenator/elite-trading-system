import { Link, useLocation, useNavigate } from "react-router-dom";
import Button from "../ui/Button";
import { logout } from "../../services/auth.service";

export default function Header({ showLogOff = true }) {
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogOut = () => {
    logout();
    navigate("/");
  };

  const isActive = (path) => {
    return location.pathname === path;
  };

  const navItems = [
    { title: "Rate Now", path: "/rank-one" },
    { title: "People Rated", path: "/ranked-people" },
    { title: "FAQ", path: "/faq" },
    { title: "My Rating", path: "/my-rating" },
  ];

  return (
    <div className="w-full flex flex-col items-center gap-2">
      <div className="w-full flex justify-between items-center mb-2">
        <a
          href="https://PopyLi.com"
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary font-semibold hover:underline text-sm"
        >
          PopyLi.com
        </a>
        {showLogOff && (
          <button
            onClick={handleLogOut}
            className="px-4 py-2 text-sm font-bold text-primary bg-transparent rounded-lg hover:bg-primary hover:text-white transition-colors duration-200"
          >
            Log Out
          </button>
        )}
      </div>

      <Link to="/faq" className="cursor-pointer">
        <img src="/EyeRL.png" alt="logo" className="w-24 h-24 rounded-xl" />
      </Link>

      <div className="w-full">
        <div className="grid grid-cols-2 gap-2">
          {navItems.map(({ title, path }) => (
            <Button
              key={title}
              title={title}
              variant="fill"
              size="sm"
              fullWidth
              onClick={() => navigate(path)}
              style={{ opacity: isActive(path) ? 0.7 : 1 }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
