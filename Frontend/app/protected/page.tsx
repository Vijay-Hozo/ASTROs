import { InfoIcon } from "lucide-react";

export default function ProtectedPage() {
  return (
    <div className="flex-1 w-full flex flex-col gap-12">
      <div className="w-full">
        <div className="bg-accent text-sm p-3 px-5 rounded-md text-foreground flex gap-3 items-center">
          <InfoIcon size="16" strokeWidth={2} />
          This dashboard is open with no login required.
        </div>
      </div>
      <div className="flex flex-col gap-2 items-start">
        <h2 className="font-bold text-2xl mb-4">Welcome</h2>
        <p className="text-sm text-muted-foreground">
          Start by creating rules or uploading XML samples.
        </p>
      </div>
    </div>
  );
}
