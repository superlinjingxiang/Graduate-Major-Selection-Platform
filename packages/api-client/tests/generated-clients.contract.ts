import { authClient, coreClient } from "../src/index.js";

const core = coreClient("https://api.example.test");
const auth = authClient("https://api.example.test");

void core.GET("/api/v1/meta");
void auth.GET("/_allauth/{client}/v1/config", {
  params: {
    path: {
      client: "browser",
    },
  },
});
