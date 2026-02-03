// hooks/useMutateCreateRubric.ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useAxiosWithAuth } from "./useAxiosWithAuth";
import { RubricData } from "./useGetEvalRubric";

interface CreateRubricParams {
  name: string;
  description?: string;
  rubric_data: RubricData;
  total_points?: number;
  dd_id?: string;
}

interface CreateRubricResponse {
  id: string;
  name: string;
  description: string | null;
  total_points: number;
  dd_id: string | null;
  created_at: string;
  created_by: string;
}

export const useMutateCreateRubric = () => {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  const createRubric = async (params: CreateRubricParams): Promise<CreateRubricResponse> => {
    const { data } = await axios({
      url: "/dd-eval-rubric-create",
      method: "POST",
      data: params,
    });
    return data;
  };

  return useMutation({
    mutationFn: createRubric,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["eval-rubrics"] });
      toast.success(`Rubric "${data.name}" created successfully!`);
    },
    onError: (error: any) => {
      console.error("Create rubric error:", error);
      const message = error.response?.data?.error || error.message || "Failed to create rubric";
      toast.error(message);
    },
  });
};
