import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function NewAgreementWelcome({ onStart }: { onStart: () => void }) {
  return (
    <div className="text-xl flex flex-1 flex-col gap-4 p-4 pt-4 justify-center h-screen">
      <div className="flex-1 rounded-xl bg-alchemyPrimaryDarkGrey">
        <div className="relative flex h-screen flex-col rounded-xl p-4 lg:col-span-2">
          <div className="flex items-center justify-center h-full">
            <div className="grid w-[60%] m-auto">
              <div className="pb-4">
                <Card className="text-3xl text-white bg-alchemyPrimaryDarkGrey border-none">
                  <CardHeader>
                    <CardTitle className="text-alchemyPrimaryOrange text-5xl font-bold tracking-wide">
                      Agreement Writer tips
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="text-xl">
                    <div className="grid grid-cols-1 border-t-2 border-white pt-4">
                      <div>
                        This activity will help you draft agreements for your
                        clients.
                        <br />
                        <br />
                        Here are some useful tips:
                        <div>
                          <ul className="list-disc pl-10">
                            <li>
                              Make the client briefing as detailed as possible
                            </li>
                            <li>
                              Find a suitable template to use as the basis for
                              this new agreement
                            </li>
                          </ul>
                        </div>
                        <div className="pt-8">
                          <Button onClick={onStart}>
                            Start a new Agreement
                          </Button>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
