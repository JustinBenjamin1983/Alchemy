import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useEffect, useState } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { SearchResults } from "./SearchResults";
import { useMutateDDSearch } from "@/hooks/useMutateDDSearch";
import { Loader2 } from "lucide-react";
import FolderPicker from "./FolderPicker";

export function Search() {
  const mutateSearch = useMutateDDSearch();
  const [screenState, setScreenState] = useState<
    "Default" | "Searching" | "Results"
  >("Default");
  const [selectedDDID, setSelectedDDID] = useState(() => {
    const query = new URLSearchParams(location.search);
    return query.get("id");
  });
  const [keywordOnly, setKeywordOnly] = useState<boolean>(false);
  const [limitSearchToFolders, setLimitSearchToFolders] =
    useState<boolean>(false);
  const [searchText, setSearchText] = useState("");

  const handleKeyDownOnSearchInput = (
    event: React.KeyboardEvent<HTMLInputElement>
  ) => {
    if (event.key === "Enter") {
      searchForDocs();
    }
  };

  const searchForDocs = () => {
    setScreenState("Searching");

    mutateSearch.mutate({
      dd_id: selectedDDID,
      folder_id: selectedFolder?.folder_id,
      prompt: searchText,
      keyword_only: keywordOnly,
    });
  };
  useEffect(() => {
    if (!mutateSearch.isSuccess) return;

    setScreenState("Results");
  }, [mutateSearch.isSuccess]);

  const [showFolderPicker, setShowFolderPicker] = useState<boolean>(false);
  const [selectedFolder, setSelectedFolder] = useState<{
    folder_id: string;
    folder_name: string;
  } | null>(null);
  return (
    <>
      <FolderPicker
        header={"Please select a folder"}
        show={showFolderPicker}
        dd_id={selectedDDID}
        onSelected={({
          folder_id,
          folder_name,
        }: {
          folder_id: string;
          folder_name: string;
        }) => {
          // alert(folder_name);
          setSelectedFolder({ folder_id: folder_id, folder_name: folder_name });
        }}
        onClosing={() => setShowFolderPicker(false)}
      />
      <div className="flex">
        <div className="pr-4 text-lg">Search Criteria</div>
        <div>
          <Input
            className="w-[300px]"
            onChange={(evt) => setSearchText(evt.target.value)}
            onKeyDown={handleKeyDownOnSearchInput}
            value={searchText}
            placeholder="Enter your search term or keyword"
          ></Input>
        </div>
        <div className="pl-4">
          <Button
            onClick={searchForDocs}
            variant="outline"
            disabled={mutateSearch.isPending || searchText.length === 0}
          >
            {mutateSearch.isPending && <Loader2 className="animate-spin" />}
            Search
          </Button>
        </div>
        <div className="pl-4">
          <div className="items-top flex space-x-2">
            <Checkbox
              checked={keywordOnly}
              onCheckedChange={(val) =>
                setKeywordOnly(val === "indeterminate" ? false : val)
              }
            />
            <div
              className="grid gap-1.5 leading-none"
              onClick={() => setKeywordOnly((s) => !s)}
            >
              <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                Keyword search
              </label>
              <p className="text-sm text-muted-foreground">
                Useful when looking for an exact phrase
              </p>
            </div>
          </div>
        </div>
        <div className="pl-4">
          <div className="items-top flex space-x-2">
            <Checkbox
              checked={limitSearchToFolders}
              onCheckedChange={(val) => {
                if (val) {
                  setShowFolderPicker(true);
                }
                setLimitSearchToFolders(val === "indeterminate" ? false : val);
                if (!val) {
                  setSelectedFolder(null);
                }
              }}
            />
            <div className="grid gap-1.5 leading-none">
              <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                Limit search to specific folders
              </label>
              <p className="text-sm text-muted-foreground">
                {selectedFolder?.folder_name && (
                  <>
                    Limiting search to{" "}
                    <strong>{selectedFolder?.folder_name}</strong>
                  </>
                )}
                {!selectedFolder?.folder_name && (
                  <>You will be able to select which folders to target.</>
                )}
              </p>
            </div>
          </div>
        </div>
      </div>
      <div className="pt-4">
        {screenState === "Searching" && (
          <div role="status" className="max-w-sm animate-pulse">
            <h3 className="h-3 bg-gray-300 rounded-full  w-48 mb-4"></h3>
            <p className="h-2 bg-gray-300 rounded-full max-w-[380px] mb-2.5"></p>
            <p className="h-2 bg-gray-300 rounded-full max-w-[340px] mb-2.5"></p>
            <p className="h-2 bg-gray-300 rounded-full max-w-[320px] mb-2.5"></p>
          </div>
        )}
        {screenState === "Results" && (
          <SearchResults
            dd_id={selectedDDID}
            results={mutateSearch?.data?.data}
            keyword={keywordOnly ? searchText : null}
            keyword_only_search={keywordOnly}
          />
        )}
      </div>
    </>
  );
}
