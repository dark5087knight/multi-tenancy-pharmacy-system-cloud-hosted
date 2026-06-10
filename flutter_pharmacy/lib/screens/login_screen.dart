import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../providers/workspace_provider.dart';
import '../services/api_service.dart';
import '../theme/theme.dart';
import '../i18n/translations.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscurePassword = true;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _submit() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);
    final workspace = Provider.of<WorkspaceProvider>(context, listen: false);
    try {
      await workspace.login(
        _emailController.text.trim(),
        _passwordController.text,
      );
    } catch (e) {
      if (e is NoAdminUserException) {
        _showAdminSetupDialog(e.tenantId);
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  void _fillCredentials(String email, String password) {
    _emailController.text = email;
    _passwordController.text = password;
  }

  @override
  Widget build(BuildContext context) {
    final appColors = Theme.of(context).extension<AppColors>()!;
    final primaryColor = Theme.of(context).colorScheme.primary;

    return Scaffold(
      backgroundColor: appColors.background,
      body: Stack(
        children: [
          // 1. Dynamic background gradient blobs
          Positioned(
            top: -100,
            right: -100,
            child: Container(
              height: 300,
              width: 300,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: primaryColor.withValues(alpha: 0.15),
              ),
            ),
          ),
          Positioned(
            bottom: -80,
            left: -80,
            child: Container(
              height: 250,
              width: 250,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: appColors.destructive.withValues(alpha: 0.08),
              ),
            ),
          ),

          Positioned(
            top: 20,
            left: 20,
            child: IconButton(
              icon: Icon(LucideIcons.settings, color: appColors.mutedForeground),
              tooltip: 'API Settings',
              onPressed: () => _showApiConfigDialog(context),
            ),
          ),

          // 2. Centered glassmorphic card container
          Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: Container(
                constraints: const BoxConstraints(maxWidth: 420),
                decoration: BoxDecoration(
                  color: appColors.surface1.withValues(alpha: 0.75),
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: appColors.border, width: 1.5),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.3),
                      blurRadius: 40,
                      offset: const Offset(0, 20),
                    ),
                  ],
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(24),
                  child: BackdropFilter(
                    filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
                    child: Padding(
                      padding: const EdgeInsets.all(32),
                      child: Form(
                        key: _formKey,
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            // Header Icon & Title
                            Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Container(
                                  padding: const EdgeInsets.all(8),
                                  decoration: BoxDecoration(
                                    color: primaryColor,
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: Icon(
                                    LucideIcons.pill,
                                    color: appColors.background,
                                    size: 24,
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Text(
                                  context.tr('login.title'),
                                  style: TextStyle(
                                    fontSize: 20,
                                    fontWeight: FontWeight.bold,
                                    color: appColors.foreground,
                                    letterSpacing: 2,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 12),
                            Text(
                              context.tr('login.subtitle'),
                              style: TextStyle(
                                  fontSize: 13,
                                  color: appColors.mutedForeground,
                                ),
                                textAlign: TextAlign.center,
                              ),
                            const SizedBox(height: 32),

                            // Email input field
                            Text(
                              context.tr('login.email'),
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                                color: appColors.mutedForeground,
                                letterSpacing: 0.5,
                              ),
                            ),
                            const SizedBox(height: 6),
                            TextFormField(
                              controller: _emailController,
                              style: TextStyle(color: appColors.foreground, fontSize: 14),
                              decoration: InputDecoration(
                                hintText: context.tr('login.email_hint'),
                                hintStyle: TextStyle(color: appColors.mutedForeground.withValues(alpha: 0.6)),
                                prefixIcon: Icon(LucideIcons.mail, size: 16, color: appColors.mutedForeground),
                                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(10),
                                  borderSide: BorderSide(color: appColors.border),
                                ),
                                enabledBorder: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(10),
                                  borderSide: BorderSide(color: appColors.border),
                                ),
                                focusedBorder: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(10),
                                  borderSide: BorderSide(color: primaryColor, width: 1.5),
                                ),
                              ),
                              validator: (val) {
                                if (val == null || val.trim().isEmpty) {
                                  return context.tr('login.email_required');
                                }
                                return null;
                              },
                            ),
                            const SizedBox(height: 20),

                            // Password input field
                            Text(
                              context.tr('login.password'),
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                                color: appColors.mutedForeground,
                                letterSpacing: 0.5,
                              ),
                            ),
                            const SizedBox(height: 6),
                            TextFormField(
                              controller: _passwordController,
                              obscureText: _obscurePassword,
                              style: TextStyle(color: appColors.foreground, fontSize: 14),
                              decoration: InputDecoration(
                                hintText: '••••••••',
                                hintStyle: TextStyle(color: appColors.mutedForeground.withValues(alpha: 0.6)),
                                prefixIcon: Icon(LucideIcons.lock, size: 16, color: appColors.mutedForeground),
                                suffixIcon: IconButton(
                                  icon: Icon(
                                    _obscurePassword ? LucideIcons.eyeOff : LucideIcons.eye,
                                    size: 16,
                                    color: appColors.mutedForeground,
                                  ),
                                  onPressed: () {
                                    setState(() => _obscurePassword = !_obscurePassword);
                                  },
                                ),
                                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(10),
                                  borderSide: BorderSide(color: appColors.border),
                                ),
                                enabledBorder: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(10),
                                  borderSide: BorderSide(color: appColors.border),
                                ),
                                focusedBorder: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(10),
                                  borderSide: BorderSide(color: primaryColor, width: 1.5),
                                ),
                              ),
                              validator: (val) {
                                if (val == null || val.isEmpty) {
                                  return context.tr('login.password_required');
                                }
                                return null;
                              },
                            ),
                            const SizedBox(height: 28),

                            // Log In Button
                            ElevatedButton(
                              style: ElevatedButton.styleFrom(
                                backgroundColor: primaryColor,
                                foregroundColor: Colors.white,
                                padding: const EdgeInsets.symmetric(vertical: 14),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                elevation: 0,
                              ),
                              onPressed: _isLoading ? null : _submit,
                              child: _isLoading
                                  ? const SizedBox(
                                      height: 18,
                                      width: 18,
                                      child: CircularProgressIndicator(
                                        color: Colors.white,
                                        strokeWidth: 2,
                                      ),
                                    )
                                  : Text(
                                      context.tr('login.login_btn'),
                                      style: const TextStyle(
                                        fontSize: 13,
                                        fontWeight: FontWeight.bold,
                                        letterSpacing: 0.5,
                                      ),
                                    ),
                            ),
                            const SizedBox(height: 28),

                            // Testing convenience accounts selector
                            Divider(color: appColors.border, height: 1),
                            const SizedBox(height: 16),
                            Text(
                              context.tr('login.quick_accounts'),
                              style: TextStyle(
                                fontSize: 9.5,
                                fontWeight: FontWeight.bold,
                                color: appColors.mutedForeground,
                                letterSpacing: 0.5,
                              ),
                              textAlign: TextAlign.center,
                            ),
                            const SizedBox(height: 12),
                            _buildQuickAccountButton(
                              context,
                              name: 'Avery Stone',
                              role: 'Admin',
                              email: 'avery@pharm.co',
                              icon: LucideIcons.shieldAlert,
                              appColors: appColors,
                              primaryColor: primaryColor,
                            ),
                            const SizedBox(height: 8),
                            _buildQuickAccountButton(
                              context,
                              name: 'Jordan Lee',
                              role: 'Pharmacist',
                              email: 'jordan@pharm.co',
                              icon: LucideIcons.pill,
                              appColors: appColors,
                              primaryColor: primaryColor,
                            ),
                            const SizedBox(height: 8),
                            _buildQuickAccountButton(
                              context,
                              name: 'Marcus Cole',
                              role: 'Cashier',
                              email: 'marcus@pharm.co',
                              icon: LucideIcons.shoppingBag,
                              appColors: appColors,
                              primaryColor: primaryColor,
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildQuickAccountButton(
    BuildContext context, {
    required String name,
    required String role,
    required String email,
    required IconData icon,
    required AppColors appColors,
    required Color primaryColor,
  }) {
    return InkWell(
      onTap: () => _fillCredentials(email, 'password123'),
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: appColors.surface2.withValues(alpha: 0.5),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: appColors.border),
        ),
        child: Row(
          children: [
            Icon(icon, size: 14, color: primaryColor),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    name,
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      color: appColors.foreground,
                    ),
                  ),
                  Text(
                    email,
                    style: TextStyle(
                      fontSize: 10,
                      color: appColors.mutedForeground,
                    ),
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: primaryColor.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                role,
                style: TextStyle(
                  fontSize: 9,
                  fontWeight: FontWeight.bold,
                  color: primaryColor,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showAdminSetupDialog(String tenantId) {
    final nameController = TextEditingController();
    final emailController = TextEditingController(text: _emailController.text);
    final passwordController = TextEditingController();
    bool isSaving = false;
    String? errorText;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setState) {
            final appColors = Theme.of(context).extension<AppColors>()!;
            final primaryColor = Theme.of(context).colorScheme.primary;

            return AlertDialog(
              backgroundColor: appColors.surface1,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              title: Row(
                children: [
                  const Icon(LucideIcons.userCheck, color: Colors.blue, size: 20),
                  const SizedBox(width: 8),
                  Text(
                    context.tr('login.setup_title'),
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      context.tr('login.setup_desc'),
                      style: const TextStyle(fontSize: 12.5, color: Colors.grey),
                    ),
                    const SizedBox(height: 16),
                    if (errorText != null) ...[
                      Text(errorText!, style: TextStyle(color: Colors.red, fontSize: 12)),
                      const SizedBox(height: 12),
                    ],
                    TextField(
                      controller: nameController,
                      style: const TextStyle(fontSize: 13),
                      decoration: InputDecoration(
                        labelText: context.tr('login.full_name'),
                        prefixIcon: const Icon(LucideIcons.user, size: 14),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: emailController,
                      style: const TextStyle(fontSize: 13),
                      decoration: InputDecoration(
                        labelText: context.tr('login.admin_email'),
                        prefixIcon: const Icon(LucideIcons.mail, size: 14),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: passwordController,
                      obscureText: true,
                      style: const TextStyle(fontSize: 13),
                      decoration: InputDecoration(
                        labelText: context.tr('login.admin_password'),
                        prefixIcon: const Icon(LucideIcons.lock, size: 14),
                      ),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: isSaving ? null : () => Navigator.pop(context),
                  child: Text(context.tr('staff.cancel'), style: TextStyle(color: appColors.mutedForeground)),
                ),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: primaryColor,
                    foregroundColor: Colors.white,
                  ),
                  onPressed: isSaving
                      ? null
                      : () async {
                          if (nameController.text.trim().isEmpty ||
                              emailController.text.trim().isEmpty ||
                              passwordController.text.trim().isEmpty) {
                            setState(() => errorText = context.tr('login.fields_required'));
                            return;
                          }
                          setState(() {
                            isSaving = true;
                            errorText = null;
                          });
                          final setupTitle = context.tr('login.setup_title');
                          final setupSuccess = context.tr('login.setup_success');
                          final workspace = Provider.of<WorkspaceProvider>(context, listen: false);
                          final nav = Navigator.of(context);

                          try {
                            await ApiService().request<dynamic>(
                              'auth/setup-admin',
                              body: {
                                'tenant_id': tenantId,
                                'name': nameController.text.trim(),
                                'email': emailController.text.trim(),
                                'password': passwordController.text,
                              },
                            );
                            if (nav.context.mounted) {
                              nav.pop();
                              workspace.showNotification(
                                title: setupTitle,
                                body: setupSuccess,
                                category: 'system',
                              );
                            }
                          } catch (err) {
                            setState(() {
                              isSaving = false;
                              errorText = err.toString().replaceAll('Exception: ', '');
                            });
                          }
                        },
                  child: isSaving
                      ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : Text(context.tr('login.create_admin_btn'), style: const TextStyle(fontWeight: FontWeight.bold)),
                ),
              ],
            );
          },
        );
      },
    );
  }

  void _showApiConfigDialog(BuildContext context) {
    final workspace = Provider.of<WorkspaceProvider>(context, listen: false);
    final urlController = TextEditingController(text: workspace.backendUrl);
    bool isSaving = false;
    String? errorText;

    showDialog(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setState) {
            final appColors = Theme.of(context).extension<AppColors>()!;
            final primaryColor = Theme.of(context).colorScheme.primary;

            return AlertDialog(
              backgroundColor: appColors.surface1,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              title: Row(
                children: [
                  Icon(LucideIcons.settings, color: primaryColor, size: 20),
                  const SizedBox(width: 8),
                  const Text(
                    'API Configuration',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text(
                    'Configure the backend API URL for this application.',
                    style: TextStyle(fontSize: 12.5, color: Colors.grey),
                  ),
                  const SizedBox(height: 16),
                  if (errorText != null) ...[
                    Text(errorText!, style: const TextStyle(color: Colors.red, fontSize: 12)),
                    const SizedBox(height: 12),
                  ],
                  TextField(
                    controller: urlController,
                    style: const TextStyle(fontSize: 13),
                    decoration: const InputDecoration(
                      labelText: 'Backend API URL',
                      prefixIcon: Icon(LucideIcons.globe, size: 14),
                    ),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: isSaving ? null : () => Navigator.pop(context),
                  child: Text('Cancel', style: TextStyle(color: appColors.mutedForeground)),
                ),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: primaryColor,
                    foregroundColor: Colors.white,
                  ),
                  onPressed: isSaving
                      ? null
                      : () async {
                          final newUrl = urlController.text.trim();
                          if (newUrl.isEmpty) {
                            setState(() => errorText = 'API URL cannot be empty');
                            return;
                          }
                          setState(() {
                            isSaving = true;
                            errorText = null;
                          });

                          try {
                            final success = await workspace.updateBackendUrl(newUrl);
                            if (success) {
                              if (context.mounted) {
                                Navigator.pop(context);
                                workspace.showNotification(
                                  title: 'API Updated',
                                  body: 'Backend API URL updated successfully.',
                                  category: 'system',
                                );
                              }
                            } else {
                              setState(() {
                                isSaving = false;
                                errorText = 'Could not connect to $newUrl';
                              });
                            }
                          } catch (err) {
                            setState(() {
                              isSaving = false;
                              errorText = err.toString().replaceAll('Exception: ', '');
                            });
                          }
                        },
                  child: isSaving
                      ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : const Text('Save', style: TextStyle(fontWeight: FontWeight.bold)),
                ),
              ],
            );
          },
        );
      },
    );
  }
}
