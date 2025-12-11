import { Top } from "@/components/Top";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useGetDDListing } from "@/hooks/useGetDDListing";
import { useGetOpinions } from "@/hooks/useGetOpinions";
import { useNavigate } from "react-router-dom";

export function ActivityChooser() {
  const navigate = useNavigate();
  const { data: opinions } = useGetOpinions();
  const { data: dds } = useGetDDListing("involves_me");

  return (
    <>
      <div className="flex items-center justify-center h-screen">
        <Top hide />
        <div className="grid w-[60%] m-auto">
          <div className="text-4xl pb-6 text-center">
            What do you want to get done?
          </div>
          <div className="pb-4">
            <Card
              className="text-2xl bg-alchemyPrimaryNavyBlue text-white cursor-pointer"
              onClick={() => navigate("/opinion")}
            >
              <CardHeader>
                <CardTitle>Opinion Writer</CardTitle>
                <CardDescription></CardDescription>
              </CardHeader>
              <CardContent className="text-lg">
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    This activity will help you write an opinion for a client.
                  </div>
                  <div>
                    {opinions?.length > 0 && (
                      <>
                        Your recent opinions:
                        <ul className="list-disc list-inside mt-2 text-gray-700 cursor-pointer">
                          {opinions?.map((opinion, idx) => {
                            return (
                              <li
                                className="cursor-pointer text-alchemySecondaryLightYellow"
                                onClick={(evt) => {
                                  evt.stopPropagation();
                                  navigate(`/opinion?id=${opinion.id}`);
                                }}
                                key={idx}
                              >
                                {opinion.title}
                              </li>
                            );
                          })}
                        </ul>
                      </>
                    )}
                  </div>
                </div>
              </CardContent>
              <CardFooter>{/* <p>Card Footer</p> */}</CardFooter>
            </Card>
          </div>
          <div className="pb-4">
            <Card
              className="text-2xl bg-alchemyPrimaryOrange text-white cursor-pointer"
              onClick={() => navigate("/dd")}
            >
              <CardHeader>
                <CardTitle>Due Diligence</CardTitle>
                <CardDescription></CardDescription>
              </CardHeader>
              <CardContent className="text-lg">
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    This activity will help you manage a data room and conduct a
                    due diligence.
                  </div>
                  {dds?.due_diligences?.length > 0 && (
                    <div>
                      The 5 most recent Due Diligences you have created or
                      joined:
                      <ul className="list-disc list-inside mt-2 text-gray-700 cursor-pointer">
                        {dds?.due_diligences?.slice(0, 5).map((dd, idx) => {
                          return (
                            <li
                              className="cursor-pointer text-alchemySecondaryLightYellow"
                              onClick={(evt) => {
                                evt.stopPropagation();
                                navigate(`/dd?id=${dd.id}`);
                              }}
                              key={idx}
                            >
                              {dd.name}
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  )}
                </div>
              </CardContent>
              <CardFooter></CardFooter>
            </Card>
          </div>

          <div className="pb-4">
            <Card
              className="text-2xl bg-alchemyPrimaryDarkGrey text-white cursor-pointer"
              onClick={() => navigate("/agreement")}
            >
              <CardHeader>
                <CardTitle>Agreement Writer</CardTitle>
                <CardDescription></CardDescription>
              </CardHeader>
              <CardContent className="text-lg">
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    This activity will help you create draft agreements.
                  </div>
                </div>
              </CardContent>
              <CardFooter></CardFooter>
            </Card>
          </div>
        </div>
      </div>
    </>
  );
}
