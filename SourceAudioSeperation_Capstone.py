# -*- coding: utf-8 -*-
"""Wave-U-net.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1hiok2PcpQZl3R01kf-V6yaN-tKfkD4Z3
"""

import tensorflow as tf
import numpy as np
from tensorflow.keras.layers import Layer

"""# Custom layers"""

class AudioClipLayer(Layer):

    def __init__(self, **kwargs):
        '''Initializes the instance attributes'''
        super(AudioClipLayer, self).__init__(**kwargs)

    def build(self, input_shape):
        '''Create the state of the layer (weights)'''
        # initialize the weights
        pass
        
    def call(self, inputs, training=None):
        '''Defines the computation from inputs to outputs'''
        
        if training:
            return inputs
        else:
            return tf.maximum(tf.minimum(inputs, 1.0), -1.0)

# Learned Interpolation layer

class InterpolationLayer(Layer):

    def __init__(self, padding = "valid", **kwargs):
        '''Initializes the instance attributes'''
        super(InterpolationLayer, self).__init__(**kwargs)
        self.padding = padding

    # def build(self, input_shape):
    #     '''Create the state of the layer (weights)''' 
    #     self.features = input_shape.as_list()[3]

    #     # initialize the weights
    #     w_init = tf.random_normal_initializer()
    #     self.w = tf.Variable(name="kernel",
    #         initial_value=w_init(shape=(self.features, ),
    #                              dtype='float32'),
    #         trainable=True)

    def build(self, input_shape):
        # Convert input_shape to a list to handle dynamic dimensions (None)
        if isinstance(input_shape, tuple):
            input_shape = list(input_shape)

        # Ensure dynamic batch size (None) doesn't interfere with processing
        if input_shape[0] is None:
            input_shape[0] = -1  # Replace None with -1 to indicate flexible batch size

        # Access features dimension safely
        self.features = input_shape[-1]  # Last dimension is the number of features
        w_init = tf.random_normal_initializer()
        self.w = tf.Variable(name="kernel",
        initial_value=w_init(shape=(self.features, ),
                                  dtype='float32'),
                              trainable=True)


    def call(self, inputs):
        '''Defines the computation from inputs to outputs'''
        w_scaled = tf.math.sigmoid(self.w)

        counter_w = 1 - w_scaled

        conv_weights = tf.expand_dims(tf.concat([tf.expand_dims(tf.linalg.diag(w_scaled), axis=0), tf.expand_dims(tf.linalg.diag(counter_w), axis=0)], axis=0), axis=0)

        intermediate_vals = tf.nn.conv2d(inputs, conv_weights, strides=[1,1,1,1], padding=self.padding.upper())

        intermediate_vals = tf.transpose(intermediate_vals, [2, 0, 1, 3])
        out = tf.transpose(inputs, [2, 0, 1, 3])
        
        num_entries = out.shape.as_list()[0]
        out = tf.concat([out, intermediate_vals], axis=0)

        indices = list()

        # num_outputs = 2*num_entries - 1
        num_outputs = (2*num_entries - 1) if self.padding == "valid" else 2*num_entries

        for idx in range(num_outputs):
            if idx % 2 == 0:
                indices.append(idx // 2)
            else:
                indices.append(num_entries + idx//2)
        out = tf.gather(out, indices)
        current_layer = tf.transpose(out, [1, 2, 0, 3])

        return current_layer

# class CropLayer(Layer):
#     def __init__(self, x2, match_feature_dim=True, **kwargs):
#         '''Initializes the instance attributes'''
#         super(CropLayer, self).__init__(**kwargs)
#         self.match_feature_dim = match_feature_dim
#         self.x2 = x2

#     def build(self, input_shape):
#         '''Create the state of the layer (weights)'''
#         # initialize the weights
#         pass
        
#     def call(self, inputs):
#         '''Defines the computation from inputs to outputs'''
#         if self.x2 is None:
#             return inputs
        
#         sum_source = inputs[0]  # The tensor you are matching
#         x2_tensor = inputs[1]   # The tensor you want to crop to match sum_source

#         target_shape = tf.shape(sum_source)  # Target shape is sum_source's shape
#         input_shape = tf.shape(x2_tensor)   # Input shape is x2_tensor's shape
        
#         # Perform cropping
#         cropped_tensor = self.crop(inputs, target_shape, self.match_feature_dim)
#         return cropped_tensor

#     def crop(self, tensor, target_shape, match_feature_dim=True):
#         '''
#         Crops a 3D tensor [batch_size, width, channels] along the width axes to a target shape.
#         Performs a centre crop. If the dimension difference is uneven, crop last dimensions first.
#         :param tensor: 4D tensor [batch_size, width, height, channels] that should be cropped. 
#         :param target_shape: Target shape (4D tensor) that the tensor should be cropped to
#         :return: Cropped tensor
#         '''
#         # Calculate the difference in the width dimension
#         input_shape=tf.shape(tensor)
#         width_diff = input_shape[1] - target_shape[1]
        
#         tf.debugging.assert_greater_equal(
#             width_diff,
#             0,
#             message="Target shape width is larger than input shape width!"
#             )

#         tf.cond(
#             tf.math.not_equal(tf.math.mod(width_diff, 2), 0),
#             lambda: tf.print("WARNING: Cropping with uneven number of extra entries on one side"),
#             lambda: tf.no_op()
#             )
#         # assert diff[1] >= 0 # Only positive difference allowed
#         cropped_tensor = tf.cond(
#             tf.equal(width_diff, 0),
#             lambda: tensor,  # No cropping needed
#             lambda: self.perform_crop(tensor, target_shape, width_diff)
#             )

#         return cropped_tensor

#     def perform_crop(self, tensor, target_shape, width_diff):
#         """Helper function to perform cropping when width_diff > 0."""
#         crop_start = width_diff // 2
#         crop_end = width_diff - crop_start

#         # Crop the width dimension
#         input_shape=tf.shape(tensor)
#         cropped_tensor = tensor[:, crop_start:input_shape[1] - crop_end, :]
#         return cropped_tensor
    
#     def compute_output_shape(self, input_shape):
#         """
#         Computes the output shape of the layer based on the cropping performed.
#         :param input_shape: The input shape of the tensor.
#         :return: The computed output shape after cropping.
#         """
#         if self.x2 is None:
#             return input_shape  # No cropping, return the same shape

#         # Adjust the width dimension based on the target tensor
#         output_shape = list(input_shape)
#         output_shape[1] = self.x2.shape[1]  # Set the width to match x2
#         return tuple(output_shape)

class CropLayer(Layer):
    def __init__(self, match_feature_dim=True, **kwargs):
        super(CropLayer, self).__init__(**kwargs)
        self.match_feature_dim = match_feature_dim

    def call(self, inputs):
        """
        Crop the first input tensor to match the shape of the second input tensor
        inputs[0]: tensor to be cropped
        inputs[1]: reference tensor for target shape
        """
        if not isinstance(inputs, list) or len(inputs) != 2:
            raise ValueError("CropLayer expects a list of exactly 2 tensors")
            
        x1, x2 = inputs
        
        # Get shapes of both tensors
        x1_shape = tf.shape(x1)
        x2_shape = tf.shape(x2)
        
        # Calculate amount to crop (should be non-negative)
        crop_amount = (x1_shape[1] - x2_shape[1])
        
        # Ensure we're not trying to crop more than we have
        tf.debugging.assert_greater_equal(
            x1_shape[1],
            x2_shape[1],
            message="First input tensor width must be greater than or equal to second input tensor width"
        )
        
        # Calculate start and end indices for center crop
        crop_start = crop_amount // 2
        crop_end = x1_shape[1] - (crop_amount - crop_start)
        
        # Perform center crop
        cropped = x1[:, crop_start:crop_end, :]
        
        return cropped

class IndependentOutputLayer(Layer):

    def __init__(self, source_names, num_channels, filter_width, padding="valid", **kwargs):
        '''Initializes the instance attributes'''
        super(IndependentOutputLayer, self).__init__(**kwargs)
        self.source_names = source_names
        self.num_channels = num_channels
        self.filter_width = filter_width
        self.padding = padding

        self.conv1a = tf.keras.layers.Conv1D(self.num_channels, self.filter_width, padding= self.padding)


    def build(self, input_shape):
        '''Create the state of the layer (weights)'''
        pass
        
    def call(self, inputs, training):
        '''Defines the computation from inputs to outputs'''
        outputs = {}
        for name in self.source_names:
            out = self.conv1a(inputs)
            outputs[name] = out
        
        return outputs

class DiffOutputLayer(Layer):

    def __init__(self, source_names, num_channels, filter_width, padding="valid", **kwargs):
        '''Initializes the instance attributes'''
        super(DiffOutputLayer, self).__init__(**kwargs)
        self.source_names = source_names
        self.num_channels = num_channels
        self.filter_width = filter_width
        self.padding = padding

        self.conv1a = tf.keras.layers.Conv1D(self.num_channels, self.filter_width, padding= self.padding)


    def build(self, input_shape):
        '''Create the state of the layer (weights)'''
        pass
        
    def call(self, inputs, training):
        '''Defines the computation from inputs to outputs'''
        outputs = {}
        # Initialize sum_source with the shape of the first output tensor (out)
        sum_source = self.conv1a(inputs[0])  # Apply the first convolution
        sum_source = AudioClipLayer()(sum_source)  # Apply the AudioClipLayer to the result
        outputs[self.source_names[0]] = sum_source
    
        for name in self.source_names[1:-1]:  # Iterate over the remaining sources
            out = self.conv1a(inputs[0])  # Apply convolution again
            out = AudioClipLayer()(out)  # Apply AudioClipLayer
            outputs[name] = out
            sum_source = sum_source + out  # Accumulate to sum_source
    
        # Apply cropping to the last source (difference from sum_source)
        last_source = CropLayer(sum_source)(inputs[1]) - sum_source
        last_source = AudioClipLayer()(last_source)
    
        outputs[self.source_names[-1]] = last_source

        return outputs

"""# Define the Network"""

# def wave_u_net(num_initial_filters = 24, num_layers = 12, kernel_size = 15, merge_filter_size = 5, 
#                source_names = ["speaker1", "speaker2"], num_channels = 1, output_filter_size = 1,
#                padding = "same", input_size = 32768, context = True, upsampling_type = "learned",
#                output_activation = "tanh", output_type = "difference"):
  
#   # `enc_outputs` stores the downsampled outputs to re-use during upsampling.
#   enc_outputs = []

#   # `raw_input` is the input to the network
#   raw_input = tf.keras.layers.Input(shape=(input_size, num_channels),name="raw_input")
#   X = raw_input
#   inp = raw_input

#   # Down sampling
#   for i in range(num_layers):
#     X = tf.keras.layers.Conv1D(filters=num_initial_filters + (num_initial_filters * i),
#                           kernel_size=kernel_size,strides=1,
#                           padding=padding, name="Down_Conv_"+str(i))(X)
#     X = tf.keras.layers.LeakyReLU(name="Down_Conv_Activ_"+str(i))(X)

#     enc_outputs.append(X)

#     X = tf.keras.layers.Lambda(lambda x: x[:,::2,:], name="Decimate_"+str(i))(X)


#   X = tf.keras.layers.Conv1D(filters=num_initial_filters + (num_initial_filters * num_layers),
#                           kernel_size=kernel_size,strides=1,
#                           padding=padding, name="Down_Conv_"+str(num_layers))(X)
#   X = tf.keras.layers.LeakyReLU(name="Down_Conv_Activ_"+str(num_layers))(X)



#   # Up sampling
#   for i in range(num_layers):
#     X = tf.keras.layers.Lambda(lambda x: tf.expand_dims(x, axis=1), name="exp_dims_"+str(i))(X)
    
#     if upsampling_type == "learned":
#       X = InterpolationLayer(name="IntPol_"+str(i), padding=padding)(X)

#     else:
#       if context:
#         X = tf.keras.layers.Lambda(lambda x: tf.image.resize(x, [1, x.shape.as_list()[2] * 2 - 1]), name="bilinear_interpol_"+str(i))(X)
#         # current_layer = tf.image.resize_bilinear(current_layer, [1, current_layer.get_shape().as_list()[2] * 2 - 1], align_corners=True)
#       else:
#         X = tf.keras.layers.Lambda(lambda x: tf.image.resize(x, [1, x.shape.as_list()[2] * 2]), name="bilinear_interpol_"+str(i))(X)
#         # current_layer = tf.image.resize_bilinear(current_layer, [1, current_layer.get_shape().as_list()[2]*2]) # out = in + in - 1


#     X = tf.keras.layers.Lambda(lambda x: tf.squeeze(x, axis=1), name="sq_dims_"+str(i))(X)
    
#     c_layer = CropLayer(X, False, name="crop_layer_"+str(i))(enc_outputs[-i-1])
#     X = tf.keras.layers.Concatenate(axis=2, name="concatenate_"+str(i))([X, c_layer]) 


#     X = tf.keras.layers.Conv1D(filters=num_initial_filters + (num_initial_filters * (num_layers - i - 1)),
#                             kernel_size=merge_filter_size,strides=1,
#                             padding=padding, name="Up_Conv_"+str(i))(X)
#     X = tf.keras.layers.LeakyReLU(name="Up_Conv_Activ_"+str(i))(X)


#   c_layer = CropLayer(X, False, name="crop_layer_"+str(num_layers))(inp)
#   X = tf.keras.layers.Concatenate(axis=2, name="concatenate_"+str(num_layers))([X, c_layer]) 
#   X = AudioClipLayer(name="audio_clip_"+str(0))(X,training=True)

#   if output_type == "direct":
#     X = IndependentOutputLayer(source_names, num_channels, output_filter_size, padding=padding, name="independent_out")(X)

#   else:
#     # Difference Output
#     cropped_input = CropLayer(X, False, name="crop_layer_"+str(num_layers+1))(inp)
#     X = DiffOutputLayer(source_names, num_channels, output_filter_size, padding=padding, name="diff_out")([X, cropped_input],training=False)

#   o = X
#   model = tf.keras.Model(inputs=raw_input, outputs=o)
#   return model

# def wave_u_net(num_initial_filters=24, num_layers=12, kernel_size=15, merge_filter_size=5,
#                source_names=["speaker1", "speaker2"], num_channels=1, output_filter_size=1,
#                padding="same", input_size=32768, context=True, upsampling_type="learned",
#                output_activation="tanh", output_type="difference"):
    
#     # Store encoder outputs for skip connections
#     enc_outputs = []
    
#     # Input layer
#     inputs = tf.keras.layers.Input(shape=(input_size, num_channels))
#     x = inputs
    
#     # Encoder (downsampling path)
#     for i in range(num_layers):
#         # Convolution
#         x = tf.keras.layers.Conv1D(
#             filters=num_initial_filters * (2**i),
#             kernel_size=kernel_size,
#             padding=padding,
#             name=f"encoder_conv_{i}"
#         )(x)
#         x = tf.keras.layers.LeakyReLU()(x)
        
#         # Store for skip connection
#         enc_outputs.append(x)
        
#         # Downsample
#         x = tf.keras.layers.Lambda(lambda x: x[:, ::2, :])(x)
    
#     # Bottleneck
#     x = tf.keras.layers.Conv1D(
#         filters=num_initial_filters * (2**num_layers),
#         kernel_size=kernel_size,
#         padding=padding,
#         name="bottleneck"
#     )(x)
#     x = tf.keras.layers.LeakyReLU()(x)
    
#     # Decoder (upsampling path)
#     for i in range(num_layers):
#         # Upsample
#         if upsampling_type == "learned":
#             x = tf.keras.layers.Lambda(lambda x: tf.expand_dims(x, axis=1))(x)
#             x = InterpolationLayer(padding=padding)(x)
#             x = tf.keras.layers.Lambda(lambda x: tf.squeeze(x, axis=1))(x)
#         else:
#             x = tf.keras.layers.UpSampling1D(size=2)(x)
        
#         # Skip connection
#         skip = enc_outputs[-(i+1)]
        
#         # Crop and concatenate
#         x = tf.keras.layers.Concatenate(axis=-1)([
#             CropLayer()([x, skip]) if x.shape[1] > skip.shape[1] else x,
#             CropLayer()([skip, x]) if skip.shape[1] > x.shape[1] else skip
#         ])
        
#         # Convolution
#         x = tf.keras.layers.Conv1D(
#             filters=num_initial_filters * (2**(num_layers-i-1)),
#             kernel_size=merge_filter_size,
#             padding=padding,
#             name=f"decoder_conv_{i}"
#         )(x)
#         x = tf.keras.layers.LeakyReLU()(x)
    
#     # Output processing
#     if output_type == "direct":
#         outputs = {}
#         for source in source_names:
#             out = tf.keras.layers.Conv1D(
#                 filters=num_channels,
#                 kernel_size=output_filter_size,
#                 padding=padding,
#                 activation=output_activation,
#                 name=f"output_{source}"
#             )(x)
#             outputs[source] = out
#     else:
#         # Difference learning
#         sum_source = tf.keras.layers.Conv1D(
#             filters=num_channels,
#             kernel_size=output_filter_size,
#             padding=padding,
#             activation=output_activation,
#             name="output_sum"
#         )(x)
        
#         outputs = {source_names[0]: sum_source}
        
#         for i in range(1, len(source_names)-1):
#             out = tf.keras.layers.Conv1D(
#                 filters=num_channels,
#                 kernel_size=output_filter_size,
#                 padding=padding,
#                 activation=output_activation,
#                 name=f"output_{source_names[i]}"
#             )(x)
#             outputs[source_names[i]] = out
#             sum_source = sum_source + out
        
#         # Last source is the difference
#         outputs[source_names[-1]] = inputs - sum_source
    
#     return tf.keras.Model(inputs=inputs, outputs=outputs)

def wave_u_net(num_initial_filters=12, num_layers=10, kernel_size=15, merge_filter_size=5,
               source_names=["speaker1", "speaker2"], num_channels=1, output_filter_size=1,
               padding="same", input_size=32768, context=True, upsampling_type="learned",
               output_activation="tanh", output_type="difference"):
    """
    Memory-efficient implementation of Wave-U-Net.
    Ensures all filter calculations result in integer values.
    Input is explicitly specified as float32.
    """
    # Store encoder outputs for skip connections
    enc_outputs = []
    
    # Input layer with explicit float32 dtype
    inputs = tf.keras.layers.Input(shape=(input_size, num_channels), dtype=tf.float32)
    x = inputs
    
    # Encoder (downsampling path)
    for i in range(num_layers):
        # Calculate number of filters and ensure it's an integer
        n_filters = int(num_initial_filters * (1.5**i))
        
        # Add batch normalization to reduce memory usage
        x = tf.keras.layers.BatchNormalization()(x)
        
        # Convolution with reduced filter size
        x = tf.keras.layers.Conv1D(
            filters=n_filters,
            kernel_size=kernel_size,
            padding=padding,
            kernel_initializer='he_normal',
            use_bias=False,  # Reduce parameters since we're using BatchNorm
            name=f"encoder_conv_{i}"
        )(x)
        x = tf.keras.layers.LeakyReLU()(x)
        
        # Store for skip connection
        enc_outputs.append(x)
        
        # Downsample
        x = tf.keras.layers.Lambda(lambda x: x[:, ::2, :])(x)
    
    # Bottleneck with reduced filters
    x = tf.keras.layers.BatchNormalization()(x)
    bottleneck_filters = int(num_initial_filters * (1.5**num_layers))
    x = tf.keras.layers.Conv1D(
        filters=bottleneck_filters,
        kernel_size=kernel_size,
        padding=padding,
        kernel_initializer='he_normal',
        use_bias=False,
        name="bottleneck"
    )(x)
    x = tf.keras.layers.LeakyReLU()(x)
    
    # Decoder (upsampling path)
    for i in range(num_layers):
        # Calculate number of filters and ensure it's an integer
        n_filters = int(num_initial_filters * (1.5**(num_layers-i-1)))
        
        # Upsample
        if upsampling_type == "learned":
            x = tf.keras.layers.UpSampling1D(size=2)(x)
        else:
            x = tf.keras.layers.UpSampling1D(size=2)(x)
        
        # Skip connection
        skip = enc_outputs[-(i+1)]
        
        # Crop and concatenate
        if x.shape[1] > skip.shape[1]:
            crop_amount = (x.shape[1] - skip.shape[1]) // 2
            x = x[:, crop_amount:-crop_amount, :]
        elif skip.shape[1] > x.shape[1]:
            crop_amount = (skip.shape[1] - x.shape[1]) // 2
            skip = skip[:, crop_amount:-crop_amount, :]
            
        x = tf.keras.layers.Concatenate(axis=-1)([x, skip])
        
        # Add batch normalization
        x = tf.keras.layers.BatchNormalization()(x)
        
        # Convolution with reduced filters
        x = tf.keras.layers.Conv1D(
            filters=n_filters,
            kernel_size=merge_filter_size,
            padding=padding,
            kernel_initializer='he_normal',
            use_bias=False,
            name=f"decoder_conv_{i}"
        )(x)
        x = tf.keras.layers.LeakyReLU()(x)
    
    # Output processing with memory-efficient implementation
    if output_type == "direct":
        outputs = {}
        for source in source_names:
            out = tf.keras.layers.Conv1D(
                filters=num_channels,
                kernel_size=output_filter_size,
                padding=padding,
                activation=output_activation,
                kernel_initializer='he_normal',
                name=f"output_{source}"
            )(x)
            outputs[source] = out
    else:
        # Difference learning
        sum_source = tf.keras.layers.Conv1D(
            filters=2,
            kernel_size=output_filter_size,
            padding=padding,
            activation=output_activation,
            kernel_initializer='he_normal',
            name="output_sum"
        )(x)
        
        outputs = {source_names[0]: sum_source}
        
        remaining_sources = tf.keras.layers.Conv1D(
            filters=2 * (len(source_names) - 1),
            kernel_size=output_filter_size,
            padding=padding,
            activation=output_activation,
            kernel_initializer='he_normal',
            name="output_remaining"
        )(x)
        
        # Split the remaining sources
        print(remaining_sources.shape)
        for i in range(1, len(source_names)):
            outputs[source_names[i]] = remaining_sources[..., (i-1):i]
    
    return tf.keras.Model(inputs=inputs, outputs=outputs)

# Parameters for the Wave-U-net

# params = {
#   "num_initial_filters": 24,
#   "num_layers": 12,
#   "kernel_size": 15,
#   "merge_filter_size": 5,
#   "source_names": ["speaker1", "speaker2"],
#   "num_channels": 1,
#   "output_filter_size": 1,
#   "padding": "same",
#   "input_size": 32768,
#   "context": True,
#   "upsampling_type": "learned",         # "learned" or "linear"
#   "output_activation": "tanh",        # "linear" or "tanh"
#   "output_type": "difference",          # "direct" or "difference" 
# }

params = {
    "num_initial_filters": 12,  # Reduced from 24
    "num_layers": 10,          # Reduced from 12
    "kernel_size": 15,
    "merge_filter_size": 5,
    "source_names": ["speaker1", "speaker2"],
    "num_channels": 1,
    "output_filter_size": 1,
    "padding": "same",
    "input_size": 32768,
    "context": True,
    "upsampling_type": "learned",
    "output_activation": "tanh",
    "output_type": "difference"
}


"""# Other utility functions"""

def get_padding(shape, num_layers=12, filter_size=15, input_filter_size=15, output_filter_size=1, merge_filter_size=5, num_channels=1, context = True):
    '''
    Note that this function is not used within the Wave-U-net. 
    But it is useful to calculate the required amounts of padding along 
    each axis of the input and output, so that the Unet works and has the 
    given shape as output shape.

    :param shape: Desired output shape 
    :return: Input_shape, output_shape, where each is a list [batch_size, time_steps, channels]
    '''

    if context:
        # Check if desired shape is possible as output shape - go from output shape towards lowest-res feature map
        rem = float(shape[1]) # Cut off batch size number and channel

        # Output filter size
        rem = rem - output_filter_size + 1

        # Upsampling blocks
        for i in range(num_layers):
            rem = rem + merge_filter_size - 1
            rem = (rem + 1.) / 2.# out = in + in - 1 <=> in = (out+1)/

        # Round resulting feature map dimensions up to nearest integer
        x = np.asarray(np.ceil(rem),dtype=np.int64)
        assert(x >= 2)

        # Compute input and output shapes based on lowest-res feature map
        output_shape = x
        input_shape = x

        # Extra conv
        input_shape = input_shape + filter_size - 1

        # Go from centre feature map through up- and downsampling blocks
        for i in range(num_layers):
            output_shape = 2*output_shape - 1 #Upsampling
            output_shape = output_shape - merge_filter_size + 1 # Conv

            input_shape = 2*input_shape - 1 # Decimation
            if i < num_layers - 1:
                input_shape = input_shape + filter_size - 1 # Conv
            else:
                input_shape = input_shape + input_filter_size - 1

        # Output filters
        output_shape = output_shape - output_filter_size + 1

        input_shape = np.concatenate([[shape[0]], [input_shape], [num_channels]])
        output_shape = np.concatenate([[shape[0]], [output_shape], [num_channels]])

        return input_shape, output_shape
    else:
        return [shape[0], shape[1], num_channels], [shape[0], shape[1], num_channels]