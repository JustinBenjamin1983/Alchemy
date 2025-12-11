import { opinionDocumentTypes } from "@/lib/utils";
import { Badge } from "./ui/badge";

export function DocTags({ tags }) {
  return (
    <div className="flex gap-2">
      {tags?.map((tag) => (
        <Badge>
          {opinionDocumentTypes.find((t) => t.value === tag)?.label}
        </Badge>
      ))}
    </div>
  );
}
