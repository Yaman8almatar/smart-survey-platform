import 'package:flutter/material.dart';

import '../../theme/app_theme.dart';
import '../../theme/tokens.dart';
import '../../widgets/signal_ring.dart';
import '../profile/profile_hero.dart';
import 'survey_parts.dart';

/// "Sent today at 17:42." or "Sent on 7 November at 17:42.", in local time;
/// another year adds it: "Sent on 7 November 2025 at 17:42.".
String sentAtText(DateTime submittedAt, DateTime now) {
  final local = submittedAt.toLocal();
  final hour = local.hour.toString().padLeft(2, '0');
  final minute = local.minute.toString().padLeft(2, '0');
  return 'Sent ${dayPhrase(local, now)} at $hour:$minute.';
}

/// Confirms a survey was sent; there is no way back to its questions.
class SurveySentScreen extends StatefulWidget {
  const SurveySentScreen({
    super.key,
    required this.title,
    required this.answered,
    required this.total,
    required this.submittedAt,
  });

  final String title;
  final int answered;
  final int total;
  final DateTime submittedAt;

  @override
  State<SurveySentScreen> createState() => _SurveySentScreenState();
}

class _SurveySentScreenState extends State<SurveySentScreen> {
  /// Starts at 0 so the ring fills and pings once after the first frame.
  int _ring = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) setState(() => _ring = 100);
    });
  }

  @override
  Widget build(BuildContext context) {
    final total = widget.total;
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) backToSurveys(context);
      },
      child: Scaffold(
        backgroundColor: SsColors.surfaceRaised,
        appBar: AppBar(
          leading: IconButton(
            tooltip: 'Close',
            icon: const Icon(Icons.close),
            onPressed: () => backToSurveys(context),
          ),
          title: Text(
            widget.title,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: SsType.heading.copyWith(color: SsColors.surfaceRaised),
          ),
        ),
        body: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              HeroBand(
                decorCenterY: SsSpace.s4 + SsLayout.ringSize / 2,
                child: Column(
                  children: [
                    SignalRing(
                      value: _ring,
                      size: SsLayout.ringSize,
                      centerIcon: Icons.check,
                      semanticLabel: 'Survey complete',
                    ),
                    const SizedBox(height: SsSpace.s4),
                    Text(
                      'Answers sent',
                      textAlign: TextAlign.center,
                      style: SsType.title.copyWith(
                        color: SsColors.surfaceRaised,
                      ),
                    ),
                    const SizedBox(height: SsSpace.s2),
                    Text(
                      'Thanks for your time. This survey is no longer in your '
                      'list.',
                      textAlign: TextAlign.center,
                      style: SsType.body.copyWith(color: SsColors.onBrandMuted),
                    ),
                  ],
                ),
              ),
              RisingSheet(
                child: ProfileContentWidth(
                  child: Padding(
                    padding: const EdgeInsetsDirectional.symmetric(
                      horizontal: SsSpace.s4,
                      vertical: SsSpace.s5,
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: SsSpace.s10,
                          height: SsSpace.s10,
                          decoration: const BoxDecoration(
                            color: SsColors.brandTint,
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(
                            Icons.check,
                            size: SsLayout.iconMedium,
                            color: SsColors.brand,
                          ),
                        ),
                        const SizedBox(width: SsSpace.s3),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '${widget.answered} of $total '
                                '${total == 1 ? 'question' : 'questions'} '
                                'answered',
                                style: SsType.body.copyWith(
                                  color: SsColors.ink,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              Text(
                                sentAtText(widget.submittedAt, DateTime.now()),
                                style: SsType.body.copyWith(
                                  color: SsColors.inkMuted,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
        bottomNavigationBar: AnswerBottomBar(
          children: [
            FilledButton(
              onPressed: () => backToSurveys(context),
              child: const Text('Back to surveys'),
            ),
          ],
        ),
      ),
    );
  }
}
