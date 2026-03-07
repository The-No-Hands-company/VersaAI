#pragma once
#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "VersaAIUnrealPlugin.generated.h"

UCLASS()
class UVersaAIUnrealPlugin : public UObject {
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category = "VersaAI")
    void SendPrompt(const FString& Prompt);
private:
    void OnResponseReceived(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful);
};
