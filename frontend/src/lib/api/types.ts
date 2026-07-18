import type { operations } from "./generated/schema";

type JsonResponse<T> = T extends { content: { "application/json": infer Body } }
  ? Body
  : never;

type RequestContent<T, ContentType extends string> = T extends {
  content: infer Content;
}
  ? ContentType extends keyof Content
    ? Content[ContentType]
    : never
  : never;

export type OperationResponse<
  Operation extends keyof operations,
  Status extends keyof operations[Operation]["responses"],
> = JsonResponse<operations[Operation]["responses"][Status]>;

export type OperationRequestBody<
  Operation extends keyof operations,
  ContentType extends string = "application/json",
> = operations[Operation] extends { requestBody?: infer RequestBody }
  ? RequestContent<NonNullable<RequestBody>, ContentType>
  : never;

export type OperationQuery<Operation extends keyof operations> =
  operations[Operation]["parameters"] extends { query?: infer Query }
    ? NonNullable<Query>
    : never;
