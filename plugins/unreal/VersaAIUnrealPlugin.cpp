// Minimal Unreal Engine plugin example (C++)
#include "VersaAIUnrealPlugin.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "Misc/Paths.h"

void UVersaAIUnrealPlugin::SendPrompt(const FString& Prompt) {
    TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(TEXT("http://localhost:5000/versaai/prompt"));
    Request->SetVerb(TEXT("POST"));
    Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
    Request->SetContentAsString(FString::Printf(TEXT("{\"prompt\": \"%s\"}"), *Prompt));
    Request->OnProcessRequestComplete().BindUObject(this, &UVersaAIUnrealPlugin::OnResponseReceived);
    Request->ProcessRequest();
}

void UVersaAIUnrealPlugin::OnResponseReceived(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful) {
    if (bWasSuccessful && Response.IsValid()) {
        FString AIResponse = Response->GetContentAsString();
        // Handle response (e.g., display in editor)
    } else {
        // Handle error
    }
}
