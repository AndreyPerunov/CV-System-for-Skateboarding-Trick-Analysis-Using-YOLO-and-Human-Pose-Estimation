import { BrowseCard } from "@/components/BrowseCard";
import { UploadCard } from "@/components/UploadCard";

export default function DashboardPage() {
  return (
    <div className="dash">
      <div className="dash-inner">
        <div className="dash-hello">
          <div>
            <h1>Analysis workspace</h1>
            <div className="sub">Upload a skate clip and we&rsquo;ll extract pose, board pose, and detected tricks.</div>
          </div>
        </div>

        <div className="action-grid">
          <UploadCard />
          <BrowseCard />
        </div>
      </div>
    </div>
  );
}
