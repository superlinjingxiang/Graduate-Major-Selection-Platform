import { authClient, coreClient } from "../src/index.js";

const core = coreClient("https://api.example.test");
const auth = authClient("https://api.example.test");

void core.GET("/api/v1/meta");
void core.GET("/api/v1/pilot-scope");
void core.GET("/api/v1/offerings");
void core.POST("/api/v1/fact-sets", {
  body: {
    confirmed_facts: {
      target_year: 2027,
      region: "北京",
    },
  },
});
void core.POST("/api/v1/corrections", {
  body: {
    offering_id: "ao_2027_bupt_081200_ft_unified_plan01",
    field_key: "eligibility.sample_rule",
    proposed_source_url: "https://yzb.example.edu/2027/rules",
    explanation: "官方来源显示该字段需要复核。",
  },
});
void auth.GET("/_allauth/{client}/v1/config", {
  params: {
    path: {
      client: "browser",
    },
  },
});
