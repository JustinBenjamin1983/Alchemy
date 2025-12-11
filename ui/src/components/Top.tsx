import { Link } from "./Link";
import { Button } from "./ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog";
import { useLocation, useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { useIdle } from "@uidotdev/usehooks";
import { useGetUser } from "@/hooks/useGetUser";
import { useEffect, useState } from "react";
import { Uploader } from "./Uploader";
import { DocLister } from "./DocLister";
import { useGetGlobalOpinionDocs } from "@/hooks/useGetGlobalOpinionDocs";
import { useMsal } from "@azure/msal-react";

export function Top({ hide = false }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { instance } = useMsal();
  const idle = useIdle(10 * 60_000);
  const { data: user } = useGetUser();
  const [showSettings, setShowSettings] = useState<boolean>(false);
  const { data: globalDocs, refetch: refetchGlobalDocs } =
    useGetGlobalOpinionDocs();

  const handleClose = (closing) => {
    setShowSettings(closing);

    setTimeout(() => {
      document.body.style.pointerEvents = "auto";
    }, 500);
  };

  const refetchDocs = () => {
    refetchGlobalDocs();
  };
  useEffect(() => {
    if (user && (user as any).likelyLoggedOut) {
      navigate("/login", {
        state: {
          message:
            "As a security measure, we have logged you out due to inactivity",
        },
      });
    }
  }, [user]);
  useEffect(() => {
    if (!idle) return;
    console.log("attempting sign out due to no activity");
    instance.logoutRedirect();
  }, [idle]);

  const path = location.pathname.replace("/", "");
  const currentMenuOptionClasses =
    "underline underline-offset-8 decoration-white decoration-2";

  return (
    <>
      {!hide && (
        <>
          <Dialog open={showSettings} onOpenChange={handleClose}>
            <DialogContent className="w-[600px]">
              <DialogHeader>
                <DialogTitle>Alchemy-wide documents</DialogTitle>
                <DialogDescription>
                  <div>
                    <Uploader
                      data={{
                        type: "save_for_global_opinion",
                      }}
                      onUploadedSuccessfully={(e) => {}}
                    />
                  </div>
                  <div className="pt-2">
                    <DocLister
                      // opinionId={selectedOpinionId}
                      // docs={loadedOpinion?.documents}
                      opinionId={null}
                      docs={null}
                      globalDocs={globalDocs?.global_documents}
                      title="Available Alchemy Opinion documents"
                      isGlobal={true}
                      allowToggling={false}
                      refresh={refetchDocs}
                    />
                  </div>
                </DialogDescription>
              </DialogHeader>
            </DialogContent>
          </Dialog>
          <header className="sticky top-0 flex h-10 items-center gap-4 border-b bg-alchemyPrimaryNavyBlue px-4 z-50 p-6">
            <nav className="hidden flex-col gap-6 text-lg font-medium md:flex md:flex-row md:items-center md:gap-5 md:text-sm lg:gap-4">
              {/* <Link
            className={cn(
              "text-foreground transition-colors hover:text-foreground",
              path == "roadmap" && currentMenuOptionClasses
            )}
          >
            <div className="w-[30px] ml-[-15px]">
              <img src="/alchemy_logo.png" />
            </div>
          </Link> */}
              <Link
                className={cn(
                  "text-foreground transition-colors hover:text-foreground",
                  path.indexOf("draft") !== -1 && currentMenuOptionClasses
                )}
                onclick={() => navigate("/opinion")}
              >
                <span className="text-white">Opinion</span>
              </Link>
            </nav>
            {/* <Sheet>
          <SheetTrigger asChild>
            <Button
              variant="outline"
              size="icon"
              className="shrink-0 md:hidden"
            >
              <Menu className="h-5 w-5" />
              <span className="sr-only">Toggle navigation menu</span>
            </Button>
          </SheetTrigger>
          <SheetContent side="left">
            <nav className="grid gap-6 text-lg font-medium">
              <Link
                onclick={null}
                className="flex items-center gap-2 text-lg font-semibold"
              >
                <div className="w-[50px]">
                  <img src="/alchemy_logo.png" />
                </div>
              </Link>
            </nav>
          </SheetContent>
        </Sheet> */}
            <div className="flex w-full items-center gap-4 md:ml-auto md:gap-2 lg:gap-4">
              <div className="ml-auto flex-1 sm:flex-initial"></div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="secondary"
                    size="icon"
                    className="rounded-full  bg-white hover:bg-white"
                  >
                    {(user as any)?.name?.substr(0, 1)}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem
                    className="cursor-pointer"
                    onClick={() => setShowSettings(true)}
                  >
                    Maintain Global Documents
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </header>
        </>
      )}
    </>
  );
}
